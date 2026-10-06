class ActivationController:
    """
    Since v3.9.0 every feature is free and its code lives in this repo. The controller is kept so that existing
    configs passing an activation_code keep working, but nothing is validated or downloaded from insomniac-bot.com.
    """
    activation_code = ""
    is_activated = True

    def validate(self, activation_code, ui=False):
        self.activation_code = activation_code
        self.is_activated = True


class ActivationRequiredException(Exception):
    pass


activation_controller = ActivationController()
