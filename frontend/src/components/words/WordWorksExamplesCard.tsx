import WorksExamples from "./WorksExamples.tsx";
import LoadingSpinner from "../common/LoadingSpinner.tsx";
import { TShakespeareWorkTitle } from "../../constants";
import FilterDropdown from "../common/FilterDropdown.tsx";
import useWordIndicesFetch from "../../hooks/words/useWordIndicesFetch.ts";
import useWordOccurrencesFiltering from "../../hooks/words/useWordOccurrencesFiltering.ts";
import { INavigationData } from "../../types/navigation.ts";

interface WordWorksExamplesProps extends INavigationData {
  word: string;
  selectedWorks: TShakespeareWorkTitle[] | null;
}


const WordWorksExamplesCard = ({
  id = "examples",
  title = "Examples from works:",
  word,
  selectedWorks,
}: WordWorksExamplesProps) => {
  const { loading, error, wordIndex } = useWordIndicesFetch(word);

  const {
    selectedOptions,
    availableOptions,
    filteredOccurrences,
    areAllOptionsDisplayed,
    handleLoadMore,
    handleOptionClick,
  } = useWordOccurrencesFiltering(wordIndex, selectedWorks);

  return (
    <div
      id={id}
      className="
        block w-3xl p-5 m-3
        border-1 rounded-lg shadow-lg
      "
    >
      <div className="flex justify-between items-start w-full">
        <p className="text-3xl font-bold font-im-fell m-3">{title}</p>
        <FilterDropdown
          availableOptions={availableOptions}
          selectedOptions={selectedOptions}
          handleOptionClick={handleOptionClick}
        />
      </div>
      {error && (<p>{error}</p>)}
      {loading && (<LoadingSpinner />)}
      {wordIndex && filteredOccurrences && (
        <WorksExamples 
          word={word}
          items={filteredOccurrences}
          areAllOptionsDisplayed={areAllOptionsDisplayed}
          handleLoadMore={handleLoadMore}
        />
      )}
    </div>
  );
};

export default WordWorksExamplesCard;
