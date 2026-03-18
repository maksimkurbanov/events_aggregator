from src.crud.base import CRUDRepository
from src.models.outbox import Outbox
from src.utils.log import get_logger

log = get_logger(__name__)


outbox_crud = CRUDRepository(model=Outbox)
