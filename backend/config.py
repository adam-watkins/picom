import os
from distutils.util import strtobool

LOCALHOST = '127.0.0.1'


class BaseConfig:
    UNIT_TESTING = False
    RAIVEN_WORKER = False

    APT_HOST = '127.0.0.1'
    API_PORT = 5000
    API_HOT_RELOAD = True
    CORS_ALLOW_ORIGINS = "http://localhost:3000"
    UPLOAD_DIR = os.path.join(os.path.dirname(
        os.path.dirname(__file__)), 'uploads')
    UPLOAD_VOLUME_ABSPATH = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'uploads')
    INTERNAL_USERNAME = 'RAIVEN_INTERNAL'
    DEFAULT_CONTAINERS = [
        {
            'name': 'Dicom Input',
            'description': 'Receive input from a DICOM node',
            'is_input_container': True
        },
        {
            'name': 'Dicom Output',
            'description': 'Send DICOM output from a DICOM node',
            'is_output_container': True
        }
    ]

    # Auth
    SECRET_KEY = 'ChangeMe'
    TOKEN_TTL = 3600

    # LDAP CONFIG
    LDAP_HOST = ''
    LDAP_PORT = 389
    LDAP_USE_SSL = False
    LDAP_USERNAME_BASE = ''
    LDAP_BASE_DN = ''
    LDAP_TEST_USR = ''
    LDAP_TEST_PW = ''
    LDAP_SEARCH_FILTER = '(&(objectCategory=person)(objectClass=user)(sAMAccountName=%s))'
    LDAP_AUTH_ENABLED = False

    # DB Config
    POSTGRES_HOST = '127.0.0.1'
    POSTGRES_USER = 'postgres'
    POSTGRES_PW = 'password'
    POSTGRES_DB = 'raiven'
    SQLALCHEMY_DATABASE_URI = ''

    # Docker
    DOCKER_URI = 'tcp://127.0.0.1:2375'
    DOCKER_HOST_OS = 'linux'

    # RabbitMQ
    RABBITMQ_HOST = '127.0.0.1'

    # Pipeline
    RAIVEN_INPUT_DIR = '/mnt/raiven/input'
    RAIVEN_OUTPUT_DIR = '/mnt/raiven/output'
    IMAGE_TAG_PREFIX = 'RAIVEN'
    PIPELINE_OUTPUT_PRE_DIR = '/app/uploads/pipeline_jobs/'
    PIPELINE_OUTPUT_SUF_DIR = '/output'

    # AE Prefixes
    PIPELINE_AE_PREFIX = 'RVP-'
    USER_AE_PREFIX = 'RVU-'
    VALID_AE_PREFIXES = (PIPELINE_AE_PREFIX, USER_AE_PREFIX)

    # DICOM
    SCP_AE_TITLE = 'RAIVEN'
    SCP_HOST = '127.0.0.1'
    SCP_PORT = 11112
    SCP_DEBUG = True

    # Return to Sender
    _RTS_HOST: str = '*'
    _RTS_PORT: int = -1

    SHAREABLE_SETTINGS = ['PIPELINE_AE_PREFIX', 'USER_AE_PREFIX']

    def __init__(self):
        env_vars = [v for v in os.environ.keys() if (
            v in vars(BaseConfig)) and not v.startswith('_')]
        [self.apply_env_var(k) for k in env_vars]

        if not os.path.exists(self.UPLOAD_DIR):
            os.mkdir(self.UPLOAD_DIR)

        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = f'postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PW}@{self.POSTGRES_HOST}/{self.POSTGRES_DB}'

        # if not hasattr(self, 'RABBITMQ_URI'):
        #     self.RABBITMQ_URI = f'amqp://{self.RABBITMQ_HOST}'

    def apply_env_var(self, env_var) -> None:
        v = os.environ[env_var]

        try:
            type_ = type(getattr(BaseConfig, env_var))
            if type_ is bool:
                v = strtobool(v)
            else:
                v = type_(v)
        except (TypeError, ValueError):
            print(
                f'[FAILED] TYPE CASTING ENV VARIABLE {env_var} TO TYPE {type(getattr(BaseConfig, env_var))}')
            print(
                f'[FAILED] ENV VARIABLE {env_var} MAY PRODUCE AN UNEXPECTED ERROR')
        finally:
            print(f'[config] {env_var}={v}')
            setattr(self, env_var, v)

    def _all_settings_to_json(self) -> dict:
        """ Should not be used due to security concerns """

        settings = {k: v for k in dir(self) if not k.startswith(
            '_') and not callable(v := getattr(self, k))}
        settings.update(vars(self))

        return settings

    def to_json(self) -> dict:
        return {k: getattr(self, k) for k in self.SHAREABLE_SETTINGS}
