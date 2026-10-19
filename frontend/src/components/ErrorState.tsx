import { describeError } from "@utils/describeError";

type ErrorStateProps = {
  error: unknown;
};

export default function ErrorState({ error }: ErrorStateProps) {
  return (
    <p className="state state--error" role="alert">
      {describeError(error)}
    </p>
  );
}
