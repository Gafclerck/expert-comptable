from app.modules.insurance import service as insurance_service
from app.modules.insurance.models import (
    InsuranceClient,
    InsuranceClientStatus,
    InsuranceContract,
    InsuranceContractStatus,
    InsurancePayment,
)
from app.modules.insurance.schemas import (
    InsuranceClientCreate,
    InsuranceClientOut,
    InsuranceContractCreate,
    InsuranceContractOut,
    InsurancePaymentCreate,
    InsurancePaymentOut,
)