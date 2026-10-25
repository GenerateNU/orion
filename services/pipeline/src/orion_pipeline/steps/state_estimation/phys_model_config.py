class PhysicsModelConfig:
    def __init__(self, model_name: str, model_params: dict):
        self.model_name = model_name
        self.model_params = model_params

    def __repr__(self):
        return f"PhysicsModelConfig(model_name={self.model_name}, model_params={self.model_params})"