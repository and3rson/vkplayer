import logging

logging.basicConfig(level='DEBUG', format='\033[95m%(relativeCreated)-13s [%(levelname)-7s]\033[0m \033[92m%(filename)s:%(lineno)s:\033[0m %(message)s')

logger = logging
