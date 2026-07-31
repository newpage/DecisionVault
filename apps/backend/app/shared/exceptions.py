class DecisionVaultException(Exception):
    pass

class NotFoundException(DecisionVaultException):
    pass

class ValidationException(DecisionVaultException):
    pass

class AuthorizationException(DecisionVaultException):
    pass
