from enum import Enum


class Role(str, Enum):
    KITCHEN = "kitchen"
    DISPATCH = "dispatch"
    STORE_MANAGER = "store_manager"
    OPS_MANAGER = "ops_manager"
    ADMIN = "admin"


# Which routes each role can access
ROLE_PERMISSIONS = {
    Role.KITCHEN: {"bake"},
    Role.DISPATCH: {"dispatch"},
    Role.STORE_MANAGER: {"store"},
    Role.OPS_MANAGER: {"bake", "dispatch", "store", "sales"},
    Role.ADMIN: {"bake", "dispatch", "store", "sales", "admin"},
}
