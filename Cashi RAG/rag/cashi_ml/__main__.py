# -*- coding: utf-8 -*-
"""Reentrenar el modelo de entidades:  python -m rag.cashi_ml

Se importa `entrenar` como módulo (no se ejecuta como __main__) para que las clases
guardadas en el .joblib conserven la ruta rag.cashi_ml.entrenar y puedan cargarse
desde el motor de Cashi.
"""
from rag.cashi_ml.entrenar import main

if __name__ == "__main__":
    main()
