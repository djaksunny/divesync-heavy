class RLController:

    def __init__(self, model_path):
        self.model = load_model(model_path)

    def get_command(self, state):
        prediction = self.model(state)
        return prediction
