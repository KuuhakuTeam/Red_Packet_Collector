"""Module for handling monetary values and currency formatting"""

class MoneyHandler:
    """Utility class for handling monetary values and currency formatting"""
    
    @staticmethod
    def str_to_float(value_str):
        """Converts monetary string value to float
        
        Args:
            value_str (str): String containing monetary value (e.g. 'R$ 10,50')
            
        Returns:
            float: Converted value, 0.0 if conversion fails
        """
        try:
            return float(value_str.replace("R$", "").replace(",", ".").strip())
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def float_to_str(value_float):
        """Converts float to formatted monetary string value
        
        Args:
            value_float (float): Numeric value to convert
            
        Returns:
            str: Formatted monetary string (e.g. 'R$ 10,50')
        """
        try:
            return f"R$ {value_float:.2f}".replace(".", ",")
        except (ValueError, AttributeError):
            return "R$ 0,00"

    @staticmethod
    def calcular_diferenca(old_value, new_value):
        """Calculates the difference between two monetary values
        
        Args:
            old_value (str): Previous monetary value as string
            new_value (str): Current monetary value as string
            
        Returns:
            str: Formatted string showing the difference with up/down arrow
        """
        try:
            v_old = MoneyHandler.str_to_float(old_value)
            v_new = MoneyHandler.str_to_float(new_value)
            difference = v_new - v_old
            
            if difference > 0:
                return f"↑ R$ {difference:.2f}".replace(".", ",")
            elif difference < 0:
                return f"↓ R$ {abs(difference):.2f}".replace(".", ",")
            return "No change"
        except Exception:
            return "Error calculating difference"
