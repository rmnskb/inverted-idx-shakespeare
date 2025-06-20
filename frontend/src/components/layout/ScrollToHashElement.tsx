import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

interface ScrollToHashElementProps {
  delay: number;
}


const ScrollToHashElement = ({
  delay = 100,
}: ScrollToHashElementProps) => {
  const location = useLocation();
  const lastHash = useRef('');

  useEffect(() => {
    if (location.hash) lastHash.current = location.hash.slice(1);

    if (lastHash.current && document.getElementById(lastHash.current)) {
      setTimeout(() => {
        document.getElementById(lastHash.current)?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
        lastHash.current = '';
      }, delay)
    }
  }, [location]);

  return null;
};

export default ScrollToHashElement;
