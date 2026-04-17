export default function AgentBadge({ status }) {
  return (
    <span className={`agent-badge badge-${status}`}>
      {status}
    </span>
  );
}
