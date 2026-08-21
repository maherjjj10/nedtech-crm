import NotificationBell from "./NotificationBell";


export default function PageHeader({
  title,
  description,
  right,
  testid,
}) {
  return (
    <div
      className="px-8 pt-8 pb-6 border-b border-border"
      data-testid={
        testid || "page-header"
      }
    >
      <div
        className="
          flex
          flex-col
          sm:flex-row
          sm:items-end
          sm:justify-between
          gap-4
        "
      >

        {/* LEFT */}
        <div>
          <h1
            className="
              text-3xl
              sm:text-4xl
              font-bold
              tracking-tight
            "
            data-testid="page-title"
          >
            {title}
          </h1>

          {description && (
            <p
              className="
                mt-2
                text-sm
                text-muted-foreground
                max-w-2xl
              "
            >
              {description}
            </p>
          )}
        </div>


        {/* RIGHT */}
        <div
          className="
            flex
            gap-2
            items-center
            self-start
            sm:self-auto
          "
        >

          {/* Notifications */}
          <NotificationBell />

          {/* Existing page buttons */}
          {right && (
            <div className="flex gap-2 items-center">
              {right}
            </div>
          )}

        </div>

      </div>
    </div>
  );
}