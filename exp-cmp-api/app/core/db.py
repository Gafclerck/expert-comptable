from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Activite cible du MVP (Etape 1) dont le super-admin devient owner au premier seed.
ASSURANCE_BUSINESS_CODE = "assurance"


def init_db(db: Session) -> None:
    from app.core.security import hash_password
    from app.modules.identity.models import (
        Business,
        BusinessAccount,
        BusinessAccountRole,
        BusinessStatus,
        Person,
        PersonStatus,
        Role,
        RoleCode,
        User,
        UserStatus,
    )

    from decimal import Decimal
    from app.modules.ledger.models import Account, AccountType, Category, CategoryType
    from app.modules.ledger.service import default_account_name_for

    roles_by_code: dict[str, Role] = {}
    for code in RoleCode:
        existing = db.query(Role).filter(Role.code == code.value).first()
        if not existing:
            existing = Role(code=code.value, name=code.value.capitalize())
            db.add(existing)
        roles_by_code[code.value] = existing

    if db.query(Business).count() == 0:
        db.add_all(
            [
                Business(code="assurance", name="Assurance", status=BusinessStatus.ACTIVE),
                Business(code="poulets", name="Poulets", status=BusinessStatus.ACTIVE),
                Business(code="vtc", name="VTC", status=BusinessStatus.ACTIVE),
            ]
        )
        db.flush()

    # Creer la caisse unique de chaque activite existante, avec un nom
    # specifique au business (jamais generique) : Assurance / Poulailler / VTC.
    businesses = db.query(Business).all()
    for b in businesses:
        has_account = db.query(Account).filter(Account.business_id == b.id).first()
        if not has_account:
            db.add(
                Account(
                    business_id=b.id,
                    name=default_account_name_for(b.code, b.name),
                    type=AccountType.CASH,
                    currency="FCFA",
                    opening_balance=Decimal("0"),
                    active=True,
                )
            )

    # Creer les categories comptables de base si absentes
    default_categories = [
        ("vente-primes", "Vente de primes", CategoryType.CREDIT),
        ("depenses-generales", "Dépenses générales", CategoryType.DEBIT),
    ]
    for code, name, ctype in default_categories:
        existing_cat = db.query(Category).filter(Category.code == code).first()
        if not existing_cat:
            db.add(Category(code=code, name=name, type=ctype))

    admin = db.query(User).filter(User.email == settings.SUPER_USER_EMAIL).first()
    if not admin:
        person = Person(full_name="Administrateur", status=PersonStatus.ACTIVE)
        db.add(person)
        db.flush()
        admin = User(
            email=settings.SUPER_USER_EMAIL,
            password_hash=hash_password(settings.SUPER_USER_PASSWORD),
            person_id=person.id,
            status=UserStatus.ACTIVE,
        )
        admin.roles = [roles_by_code[RoleCode.ROOT.value]]
        db.add(admin)
        db.flush()

    assurance = db.query(Business).filter(Business.code == ASSURANCE_BUSINESS_CODE).first()
    if admin.person_id is not None and assurance is not None:
        is_owner = (
            db.query(BusinessAccount)
            .filter(
                BusinessAccount.business_id == assurance.id,
                BusinessAccount.person_id == admin.person_id,
                BusinessAccount.role == BusinessAccountRole.OWNER,
            )
            .first()
        )
        if is_owner is None:
            db.add(
                BusinessAccount(
                    business_id=assurance.id,
                    person_id=admin.person_id,
                    role=BusinessAccountRole.OWNER,
                )
            )

    db.commit()