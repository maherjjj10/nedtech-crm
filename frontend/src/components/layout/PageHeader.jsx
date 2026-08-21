export default function PageHeader({
  title,
  description,
  right,
  testid,
}) {
  return (
    <div
      className="
        w-full
        border-b border-border
        px-4 py-5
        sm:px-6 sm:py-6
        lg:px-8 lg:pt-8 lg:pb-6
      "
      data-testid={testid || "page-header"}
    >
      <div
        className="
          flex
          flex-col
          gap-4
          sm:flex-row
          sm:items-end
          sm:justify-between
        "
      >

        <div className="min-w-0">
          <h1
            className="
              text-2xl
              font-bold
              tracking-tight
              sm:text-3xl
              lg:text-4xl
            "
            data-testid="page-title"
          >
            {title}
          </h1>

          {description && (
            <p
              className="
                mt-2
                max-w-2xl
                text-sm
                leading-6
                text-muted-foreground
              "
            >
              {description}
            </p>
          )}
        </div>


        {right && (
          <div
            className="
              flex
              w-full
              flex-wrap
              items-center
              gap-2
              sm:w-auto
              sm:shrink-0
            "
          >
            {right}
          </div>
        )}

      </div>
    </div>
  );
}