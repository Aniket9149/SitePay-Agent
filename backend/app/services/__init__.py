#Owner::ANIKET::ANHOTRA = MR.Panda
"""Business services. They hold the rules and work on a database session.

Services do not commit. The route that called them decides when the transaction ends.
The one exception is refresh token theft detection in auth_service, which must save
its revocation even though the request then fails.
"""
