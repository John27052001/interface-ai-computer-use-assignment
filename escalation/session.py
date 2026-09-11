class SessionControl:

    def __init__(self):

        self.owner = "automation"
        self.state = "running"


    def hand_to_human(self):

        self.owner = "human"
        self.state = "paused"


    def return_to_automation(self):

        self.owner = "automation"
        self.state = "running"


    def get_status(self):

        return {
            "owner": self.owner,
            "state": self.state
        }