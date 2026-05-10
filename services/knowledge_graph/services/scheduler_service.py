import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from services.proposal_service import GraphProposalService


class SchedulerService:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.proposal_service = GraphProposalService(config=config)
        self.state_file = Path(self.config.get("scheduler_state_file", ".scheduler_state.json"))

    def load_state(self) -> dict[str, Any]:
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "last_run": None,
            "proposals_created": [],
            "queries": [],
        }

    def save_state(self, state: dict[str, Any]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def add_query(self, query: str, source: str = "gdelt", days: int = 7, schedule: str = "daily") -> dict[str, Any]:
        state = self.load_state()
        query_config = {
            "query": query,
            "source": source,
            "days": days,
            "schedule": schedule,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        state["queries"].append(query_config)
        self.save_state(state)
        return {"status": "added", "query": query_config}

    def run_scheduled_queries(self) -> list[dict[str, Any]]:
        state = self.load_state()
        results = []

        for query_config in state["queries"]:
            if not query_config.get("enabled", True):
                continue

            schedule = query_config.get("schedule", "daily")
            last_run = query_config.get("last_run")

            if self._should_run(schedule, last_run):
                try:
                    result = self.proposal_service.create_proposal_from_news(
                        source=query_config["source"],
                        query=query_config["query"],
                        graph_name=f"Auto: {query_config['query'][:50]}",
                        days=query_config["days"],
                        created_by="scheduler",
                    )

                    if result["status"] == "success":
                        proposal = result["proposal"]
                        saved = self.proposal_service.save_proposal(proposal)
                        query_config["last_run"] = datetime.utcnow().isoformat()
                        query_config["last_proposal_id"] = proposal["proposal_id"]
                        results.append({
                            "status": "success",
                            "query": query_config["query"],
                            "proposal_id": proposal["proposal_id"],
                            "graph_id": saved.get("graph_id"),
                        })

                except Exception as e:
                    results.append({
                        "status": "error",
                        "query": query_config["query"],
                        "error": str(e),
                    })

        self.save_state(state)
        return results

    def _should_run(self, schedule: str, last_run: str | None) -> bool:
        if not last_run:
            return True

        last_run_dt = datetime.fromisoformat(last_run)
        now = datetime.utcnow()

        if schedule == "daily":
            return (now - last_run_dt) >= timedelta(days=1)
        elif schedule == "hourly":
            return (now - last_run_dt) >= timedelta(hours=1)
        elif schedule == "weekly":
            return (now - last_run_dt) >= timedelta(weeks=1)
        else:
            return False

