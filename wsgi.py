from linkapp.tag.wsgi import TagMicroservice
from linkapp.tag.config import TagConfig

config = TagConfig()

app = TagMicroservice(config)