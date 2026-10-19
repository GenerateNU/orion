type LoadingStateProps = {
  message?: string;
};

export default function LoadingState({ message = "Loading…" }: LoadingStateProps) {
  return (
    <p className="state state--loading" role="status">
      {message}
    </p>
  );
}
