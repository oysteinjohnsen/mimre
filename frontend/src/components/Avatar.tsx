import type { Person } from "../api";
import { avatarColor, initials } from "../lib/format";

const SIZES = {
  sm: "size-9 text-sm",
  lg: "size-16 text-xl",
};

export function Avatar({ person, size = "sm" }: { person: Person; size?: keyof typeof SIZES }) {
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${SIZES[size]} ${avatarColor(person.id)}`}
    >
      {initials(person)}
    </span>
  );
}
