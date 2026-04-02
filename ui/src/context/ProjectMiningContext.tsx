import { createContext, useContext, useRef, useState, type ReactNode } from "react";
import { api } from "../api/apiClient";

type ProjectMiningContextType = {
  isProjectMining: boolean;
  startMining: (file: File) => void;
};

const ProjectMiningContext = createContext<ProjectMiningContextType>({
  isProjectMining: false,
  startMining: () => {},
});

export function ProjectMiningProvider({ children }: { children: ReactNode }) {
  const [isProjectMining, setIsProjectMining] = useState(false);
  const miningRef = useRef(false);

  function startMining(file: File) {
    if (miningRef.current) return;
    miningRef.current = true;
    setIsProjectMining(true);
    api.uploadProject({ file }).finally(() => {
      miningRef.current = false;
      setIsProjectMining(false);
    });
  }

  return (
    <ProjectMiningContext.Provider value={{ isProjectMining, startMining }}>
      {children}
    </ProjectMiningContext.Provider>
  );
}

export function useProjectMining() {
  return useContext(ProjectMiningContext);
}
