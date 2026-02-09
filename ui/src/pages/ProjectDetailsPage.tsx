import { useParams } from "react-router-dom";

export default function ProjectDetailsPage() {
  const { id } = useParams();

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ marginTop: 0 }}>Project Details</h1>
      <p>
        TODO: Fetch and render details for project id: <code>{id}</code>
      </p>
      <p>
        Endpoint: <code>GET /projects/{`{id}`}</code>
      </p>
    </div>
  );
}