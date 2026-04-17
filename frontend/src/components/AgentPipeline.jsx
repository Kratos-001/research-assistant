import AgentBadge from "./AgentBadge";

const AGENTS = [
  {
    key: "retrieval",
    name: "Retrieval Agent",
    desc: "Finds relevant passages from your document",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 2.25c0 2.278-3.694 4.125-8.25 4.125S3.75 10.903 3.75 8.625m16.5 2.25c0 2.278-3.694 4.125-8.25 4.125S3.75 13.153 3.75 10.875" />
      </svg>
    ),
  },
  {
    key: "factcheck",
    name: "Fact-Check Agent",
    desc: "Verifies claims against document content",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
  },
  {
    key: "analysis",
    name: "Analysis Agent",
    desc: "Delivers rich multi-dimensional insights",
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
      </svg>
    ),
  },
];

function getAgentStatus(agentKey, activeAgent, status) {
  if (status === "idle") return "idle";
  if (status === "routing" || status === "uploading") return "routing";
  if (status === "running" || status === "done" || status === "error") {
    if (agentKey === activeAgent) {
      return status === "running" ? "active" : "done";
    }
    return "idle";
  }
  return "idle";
}

export default function AgentPipeline({ status, activeAgent, routingReason }) {
  const isOrchestrating = ["uploading", "routing"].includes(status);
  const isActive = status !== "idle";

  return (
    <div className="pipeline-section">
      <div className="pipeline-header">Agent Pipeline</div>

      {/* Orchestrator node */}
      <div className={`orchestrator-node${isOrchestrating ? " active" : ""}`}>
        <div className="orchestrator-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <span className="orchestrator-label">Orchestrator</span>
        {isOrchestrating && <div className="orchestrator-spinner" />}
        {status === "done" && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="2" style={{ marginLeft: "auto" }}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
          </svg>
        )}
      </div>

      {routingReason && (
        <p className="routing-reason">"{routingReason}"</p>
      )}

      {isActive && (
        <div className="route-arrow">
          <div className="route-arrow-line" />
          <span>routes to</span>
          <div className="route-arrow-line" />
        </div>
      )}

      {/* Agent cards */}
      <div className="agents-row">
        {AGENTS.map((agent) => {
          const agentStatus = getAgentStatus(agent.key, activeAgent, status);
          const cardClass = [
            "agent-card",
            agentStatus === "active" ? "active" : "",
            agentStatus === "done" ? "done" : "",
            status !== "idle" && agentStatus === "idle" ? "" : "",
            status === "idle" ? "idle-visible" : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <div key={agent.key} className={cardClass}>
              <div className="agent-icon">{agent.icon}</div>
              <div className="agent-name">{agent.name}</div>
              <div className="agent-desc">{agent.desc}</div>
              <AgentBadge status={agentStatus} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
