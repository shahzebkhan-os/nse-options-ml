import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
import pickle

class StockPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        
    def prepare_data(self, df, feature_cols):
        """
        Prepares data for the Neural Network.
        """
        X = df[feature_cols].values
        y = df['Target'].values
        
        X_scaled = self.scaler.fit_transform(X)
        
        return X_scaled, y, self.scaler
        
    def build_model(self, input_shape=None):
        """
        Builds a Multi-layer Perceptron Neural Network.
        """
        # MLP similar to the previous LSTM structure in depth
        self.model = MLPClassifier(hidden_layer_sizes=(64, 32, 16),
                                   activation='relu',
                                   solver='adam',
                                   max_iter=500,
                                   random_state=42)
        return self.model
        
    def train(self, X_train, y_train, epochs=None, batch_size=None):
        # Epochs/batch_size are handled by max_iter/internal logic in sklearn or defaults
        self.model.fit(X_train, y_train)
        
    def predict(self, X):
        # Returns probability of class 1 (Bullish)
        return self.model.predict_proba(X)[:, 1]
