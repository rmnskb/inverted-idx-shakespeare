import os
import re
import random
import hashlib
from typing import Optional, TypeVar, TypeAlias
from collections import defaultdict
from itertools import groupby
from datetime import date

import pymongo
from pymongo import AsyncMongoClient

from .models import (
    InvertedIndexItem, TokensItem, WordDimensionsItem, 
    CollocationsStatsItem, SuggestionsItem, WordOfTheDayItem
)

T = TypeVar('T')
MongoFilterType: TypeAlias = dict[str, str]


class _MongoRepository:

    def __init__(self):
        uri = self._get_conn_uri()
        self._client = AsyncMongoClient(uri)

    @staticmethod
    def _get_conn_uri() -> str:
        user = os.getenv("DB_API_USER")
        pwd = os.getenv("DB_API_PWD")
        host = "mongodb"
        port = 27017

        return f"mongodb://{user}:{pwd}@{host}:{port}/shakespeare?authSource=shakespeare"

    @property
    def client(self) -> AsyncMongoClient:
        return self._client


class ShakespeareRepository(_MongoRepository):

    def __init__(self):
        super().__init__()
        self._db = self.client['shakespeare']
 
    async def create_indices(self) -> None:
        await self._db.bronzeIndices.create_index(
            [("word", "text")]
        )

    @staticmethod
    def _get_deterministic_seed(target_date: date) -> int:
        date_string = target_date.isoformat()
        hash_obj = hashlib.sha256(date_string.encode())

        return int.from_bytes(hash_obj.digest()[:8], byteorder="big")

    async def find_word(self, word: str) -> InvertedIndexItem:
        """
        Return the best match for the given word,
        works like SQL LIKE %word% query

        :param word: the search criteria
        :return: BSON match output
        """
        regexp = re.compile(rf"^{word}$", re.IGNORECASE)

        result = await self._db.bronzeIndices.find_one({"word": regexp})

        if result:
            return InvertedIndexItem(**result)

    async def find_words(self, words: list[str]) -> list[InvertedIndexItem]:
        results: list[InvertedIndexItem] = []

        for word in words:
            if item := await self.find_word(word):
                results.append(item)

        return results

    async def find_tokens(self, document: str, start: int, limit: int) -> TokensItem:
        """
        Get the tokens (words) from the given document
        :param document: name of the document
        :param start: start position of the tokens slice
        :param limit: number of tokens to return
        :return: a hash map of document and respective tokens within given range
        """
        result = await self._db.bronzeTokens.find_one(
            {"document": document}
            , {"occurrences": {"$slice": [start, limit]}}
        )

        if result:
            return TokensItem(**result)

    async def find_phrase_indices(self, words: list[str]) -> dict[str, list[list[int]]]:
        """
        Find in what documents and where in particular given words appear together
        :param words: a list of words, i.e a phrase (e.g. "All that glisters is not gold")
        :return: a dictionary with document name as key and a list of indices as value
        """

        def find_docs_intersection(attributes: list[dict[str, ...]]) -> Optional[set[str]]:
            """
            Traverse the list of given words,
            find the documents that are common for all documents
            :param attributes: list of all and their respective attributes
            :return: a set of common documents
            """
            documents_hash: dict[str, set[str]] = {
                item['word']: set([document['document'] for document in item['occurrences']])
                for item in attributes
            }

            # Find the intersection of all documents
            docs: set[str] = set()
            for _, documents in documents_hash.items():
                docs = documents.copy() if not docs else docs.intersection(documents)

            return docs

        def get_consecutive_subsequences(sequence: list[T], length: int) -> list[list[T]]:
            """
            Divide the list into subsequences of length n, if there are no subsequences, return an empty list
            :param sequence: a list to draw the subsequences from
            :param length: the length of the subsequences to return
            :return: a list of subsequences of the given length
            """
            sorted_seq = sorted(sequence)

            runs = []
            current_run = [sorted_seq[0]]

            for i in range(1, len(sorted_seq)):
                if sorted_seq[i] == sorted_seq[i - 1] + 1:
                    current_run.append(sorted_seq[i])
                else:
                    if len(current_run) >= length:
                        runs.append(current_run[:])
                    current_run = [sorted_seq[i]]

            if len(current_run) >= length:
                runs.append(current_run)

            if not runs:
                return []

            outcome = []
            for run in runs:
                for i in range(len(run) - length + 1):
                    outcome.append(run[i: i + length])

            return outcome

        # TODO: define local-scope type aliases for this mess
        def get_adjacent_indices(docs_occur: dict[str, list[int]], n: int) -> dict[str, list[list[int]]]:
            """
            Get the indices of words that are adjacent in the given documents
            :param docs_occur: a dictionary mapping words indices to documents
            :param n: number of words to check against
            :return:
            """
            # Yes, a lambda function as a variable, mentally preparing myself for TS + React frontend part
            # Btw courtesy of https://stackoverflow.com/questions/42868875
            calculate_adjacent_diff = lambda array: [(array[i] - array[i + 1]) for i in range(0, len(array) - 1)]
            adjacent_indices = {}

            for document, occurs in docs_occur.items():
                unique_occurs = sorted(list(set(occurs)))
                adjacent_diff = calculate_adjacent_diff(unique_occurs)

                # To avoid partial matches,
                # the number of adjacent words must match with the number of words in the query,
                # and they must be consecutive
                no_adjacent_elems = -1 not in adjacent_diff
                diffs_not_consecutive = [-1] * (n - 1) not in [list(group[1]) for group in groupby(adjacent_diff)]

                if no_adjacent_elems or diffs_not_consecutive:
                    continue

                # Get the list of indices of the words that are adjacent
                indices = [(i, i + 1) for i, val in enumerate(adjacent_diff) if val == -1]
                flat_indices = list(sum(indices, ()))  # Flatten the list of indices
                adjacent_occurrences = list(set([unique_occurs[i] for i in flat_indices]))
                adjacent_indices[document] = get_consecutive_subsequences(adjacent_occurrences, length=n)

            return adjacent_indices

        results_raw = await self.find_words(words=words)
        results = [item.model_dump() for item in results_raw]  # Convert the pydantic models to Python dicts
        words_num = len(words) if isinstance(words, list) else 1

        common_docs = find_docs_intersection(attributes=results)
        document_occurrences: dict[str, list[int]] = defaultdict(list)

        for result in results:
            for occurrence in result['occurrences']:
                document_occurrences[occurrence['document']].extend(
                    occurrence['indices'] if occurrence['document'] in common_docs else []
                )

        return get_adjacent_indices(docs_occur=document_occurrences, n=words_num)

    async def find_matches(self, word: str) -> list[InvertedIndexItem]:
        """
        Find matches for a given word using mongo's built-in text search
        :param word: a textual representation of human sounds, what do you think it might be
        :return: a list of InvertedIndexItem objects containing the matches
        """
        results: list[InvertedIndexItem] = []

        async for result in self._db.bronzeIndices.find(
                {"$text": {"$search": word}},
                {"score": {"$meta": "textScore"}}
        ).sort("score", pymongo.ASCENDING):
            if result is not None:
                results.append(InvertedIndexItem(**result))

        if results:
            return results

    async def get_stats(self, word: str) -> WordDimensionsItem:
        """
        Get statistics (frequencies per document or per year) for a given word
        :param word: a word that you think Shakespeare might have used
        :return: dimensions (freq per year, freq per document) per word
        """
        result = await self._db.goldWords.find_one({"word": word})

        if result:
            return WordDimensionsItem(**result)

    async def get_document(self, document: str) -> TokensItem:
        result = await self._db.bronzeTokens.find_one({"document": document})

        if result:
            return TokensItem(**result)

    async def get_collocations_stats(self, word: str) -> CollocationsStatsItem:
        result = await self._db.silverCollocationsStats.find_one({"word": word})

        if result:
            return CollocationsStatsItem(**result)
 
    async def get_autosuggestions(self, q: str, limit: int) -> SuggestionsItem:
        pattern = re.escape(q)

        results = await self._db.bronzeIndices.find(
            {
                'word': {
                    '$regex': pattern,
                    '$options': 'i'
                },
            }, {'word': 1, '_id': 0,}
        ).limit(limit).to_list(None)

        suggestions = [result['word'] for result in results if 'word' in result]
 
        if results:
            return SuggestionsItem(suggestions=suggestions)

    async def _get_total_word_count(self, filter: Optional[MongoFilterType] = {}) -> int:
        return await self._db.bronzeIndices.count_documents(filter)

    async def _get_word_by_index(self, idx: int, filter: Optional[MongoFilterType] = {}) -> Optional[InvertedIndexItem]:
        cursor = self._db.bronzeIndices.find(filter).skip(idx).limit(1)
        document = await cursor.to_list(length=1)

        if not document:
            return None

        return InvertedIndexItem(**document[0])

    async def get_random_word(self, target_date: Optional[date] = None, length: Optional[int] = None) -> WordOfTheDayItem:
        if length:
            pattern = fr'^\w{{{length}}}$'  # Horrendous, yet effective :/ 
            filter = {'word': {'$regex': pattern}}
        else:
            filter = {}

        is_random = target_date is None
        total_cnt = await self._get_total_word_count(filter=filter)

        if target_date:
            seed = self._get_deterministic_seed(target_date)

            random.seed(seed)
            word_idx = random.randint(0, total_cnt - 1)
            random.seed()

            response_date = target_date
        else:
            word_idx = random.randint(0, int(total_cnt) - 1)
            response_date = date.today().isoformat()

        document = await self._get_word_by_index(word_idx, filter=filter)

        return WordOfTheDayItem(
            word=document.word,
            date=response_date,
            is_random=is_random,
        )

