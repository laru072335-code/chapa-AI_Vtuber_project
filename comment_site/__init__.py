from quart  import Quart

app = Quart(__name__)
app.config.from_object('comment_site.config')

import comment_site.view
