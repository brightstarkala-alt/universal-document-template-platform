import { useContext } from "react";
import { CompanyContext } from "@/contexts/company-context";

export function useCompany() {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error("useCompany must be used within a CompanyProvider");
  }
  return context;
}
