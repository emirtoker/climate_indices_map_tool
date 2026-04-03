import numpy as np

def apply_visualization_logic(data, mode, params):
    """
    Kullanici secimine gore veriyi filtreler.
    mode: 'Interval' veya 'Threshold'
    """
    processed_data = data.copy()
    
    if mode == "Interval":
        # vmin ve vmax disindakileri NaN yapma (istege bagli) veya clip etme
        vmin, vmax = params['vmin'], params['vmax']
        processed_data = processed_data.where((processed_data >= vmin) & (processed_data <= vmax))
        
    elif mode == "Threshold":
        threshold = params['threshold']
        # Esik degerden kucukleri tamamen seffaf (NaN) yap
        processed_data = processed_data.where(processed_data >= threshold)
        # Esik degerden buyukleri tek bir sabit renge boyamak istersek 
        # burada veriyi 1'e de esitleyebiliriz.
        
    return processed_data
