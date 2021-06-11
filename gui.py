import sys
import logging
from mv7config.gui import Application

logging.basicConfig(
    format="[%(levelname)8s] %(name)s: %(message)s",
    level=logging.DEBUG,
)

app = Application()
app.run(sys.argv)
