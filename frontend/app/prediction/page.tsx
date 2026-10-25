import { CustomerDashboard } from "@/components/customer/CustomerDashboard";

export const metadata = {
  title: "GridAware — Outage Prediction",
  description: "Customer service context and storm outage risk simulator",
};

export default function PredictionPage() {
  return <CustomerDashboard />;
}
