class NormalizationFailureException(Exception):
    """
    Exception raised when a normalization operation fails.

    This exception is typically raised when an attempt to normalize
    coordinates results in values outside the expected range of 0 to 1.

    :ivar message: The error message
    """

    def __init__(self, message: str):
        """
        Initialize the NormalizationFailureException with a default error message.
        """
        super().__init__(message)


class ScalingFailureException(Exception):
    """
    Exception raised when a scaling operation fails.

    This exception is typically raised when an attempt to scale
    normalized coordinates to pixel coordinates results in unexpected values.

    :ivar message: The error message
    """

    def __init__(self, message: str):
        """
        Initialize the ScalingFailureException with a default error message.
        """
        super().__init__(message)
