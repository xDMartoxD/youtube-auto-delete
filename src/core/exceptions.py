class YoutubeAutoDeleteApiError(Exception):
    """base exception class"""

    def __init__(
        self,
        message: str = "Service is unavailable",
        name: str = "YoutubeAutoDeleteAPI",
        user_message: str = "Service is unavailable",
    ) -> None:
        self.message = message
        self.name = name
        self.user_message = user_message
        super().__init__(self.message, self.name, self.user_message)


class AuthenticationFailedError(YoutubeAutoDeleteApiError):
    """Invalid auth credentials"""

    pass


class AwsFailedError(YoutubeAutoDeleteApiError):
    """Invalid auth credentials"""

    pass
