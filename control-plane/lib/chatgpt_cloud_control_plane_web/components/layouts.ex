defmodule ChatGPTCloudWeb.Layouts do
  use ChatGPTCloudWeb, :html

  def root(assigns) do
    ~H"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="csrf-token" content={Phoenix.Controller.get_csrf_token()} />
        <title>ChatGPT Cloud Process Intelligence</title>
        <link phx-track-static rel="stylesheet" href="/assets/css/app.css" />
        <script defer phx-track-static type="text/javascript" src="/assets/js/app.js"></script>
      </head>
      <body>
        {@inner_content}
      </body>
    </html>
    """
  end
end
