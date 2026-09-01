from app.modules.audit.models import AuditAction, AuditLog
from app.modules.audit.service import attach_listeners, list_logs, record, to_out