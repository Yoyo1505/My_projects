# Model Card: RAG Baseline vs. Fine-Tuning (LoRA / QLoRA)

## 1. Evaluación del Baseline RAG vs Fine-Tuning
En proyectos de análisis financiero corporativo y reporteo territorial, la exactitud numérica y el **cero nivel de alucinación** son requisitos críticos.

### Comparativo Técnico

| Criterio | Baseline RAG (Implementado) | Fine-Tuning (LoRA / QLoRA) |
|---|---|---|
| **Precisión de Cifras** | **100% Determinista** (Lee fuentes Parquet/DuckDB vigentes). | **Riesgo de Alucinación** (Memorización difusa de valores). |
| **Citas y Linaje** | **Citas Exactas** (Ruta de archivo, sección y líneas). | No ofrece citas verificables nativas. |
| **Actualización de Datos** | **Inmediata** (Re-indexado en segundos tras actualizar datos). | Requiere re-entrenamiento continuo ($ y tiempo). |
| **Consumo de Recursos** | **Extremadamente Bajo** (< 150 MB RAM, sin GPU). | Alto (Requiere VRAM GPU 8GB+ / 16GB+ para cuantización PEFT). |
| **Privacidad Local** | **100% Local-First** (Sin exfiltración de datos). | Requiere descarga/ejecución de LLM local pesado. |

## 2. Conclusión y Recomendación
Se adopta el **Baseline RAG Híbrido (BM25 + Ponderación por Términos clave)** como la solución primaria.

El fine-tuning mediante LoRA/QLoRA se reserva exclusivamente como un componente opcional para tareas de clasificación sintáctica de intenciones en lenguaje natural (NLU), pero **nunca para la generación de montos ni reglas financieras**, garantizando que los cálculos sigan ejecutándose con código Python y DuckDB determinista.
