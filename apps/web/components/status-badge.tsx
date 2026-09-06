import { Badge } from "@/components/ui/badge"

type HunarCallStatus =
  | "NOT_STARTED"
  | "SCHEDULED"
  | "INITIATED"
  | "RINGING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "NOT_CONNECTED"
  | "FAILED"
  | "CANCELLED"

const statusStyles: Record<HunarCallStatus, string> = {
  NOT_STARTED: "bg-gray-100 text-gray-700 hover:bg-gray-100",
  SCHEDULED: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  INITIATED: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  RINGING: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  IN_PROGRESS: "bg-blue-100 text-blue-700 hover:bg-blue-100",
  COMPLETED: "bg-green-100 text-green-700 hover:bg-green-100",
  NOT_CONNECTED: "bg-red-100 text-red-700 hover:bg-red-100",
  FAILED: "bg-red-100 text-red-700 hover:bg-red-100",
  CANCELLED: "bg-red-100 text-red-700 hover:bg-red-100",
}

export function StatusBadge({ status }: { status: string }) {
  const normalizedStatus = status.toUpperCase() as HunarCallStatus
  return (
    <Badge className={statusStyles[normalizedStatus] || "bg-gray-100 text-gray-700 hover:bg-gray-100"}>
      {status.replaceAll("_", " ")}
    </Badge>
  )
}
