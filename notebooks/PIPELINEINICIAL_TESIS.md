A continuación se construye un plan de entregables parciales para el próximo mes, específicamente adaptado al dataset SHIDC-B-Ki-67. Primero va un resumen de los hitos clave y luego los detalles de cada etapa con su cronograma semanal:
(esto luego de la exploración por caso de imagenes en un editor normal (yo tengo uno web))

En cuatro semanas se tendría un “pipeline mínimo” que:

1. Se carga un subconjunto representativo de imágenes del SHIDC-B-Ki-67.
2. Aplicamos normalización de contraste con CLAHE sobre esas imágenes.
3. Ejecutamos aumentación de datos con Albumentations para enriquecer el subset.
4. Se realiza un conteo básico de núcleos (por umbral y detección de contornos) y genere un reporte con recuentos por imagen.

## 1. Subconjunto de datos

* **Descripción del dataset**: SHIDC-B-Ki-67 contiene 1 656 imágenes de entrenamiento y 701 de test, con un promedio de 69 células anotadas por imagen ([Nature][1]).
* **Selección manual**: Se escogerá un subset de \~50 imágenes (por ejemplo, 10 imágenes de cada clase: Ki-67 positivo, Ki-67 negativo, TILs) que cubra distintas variaciones de tinción y calidad.

## 2. Carga y preprocesamiento inicial

* **Data loader**: Se implementará un cargador en PyTorch o TensorFlow que lea las imágenes y los archivos de anotación CSV/JSON. Me puedo basar en el repositorio PathoNet que ofrece un loader para SHIDC-B-Ki-67 ([paperswithcode.com][2]).
* **Visualización rápida**: Luego, se mostrará en un Jupyter notebook 5–10 ejemplos del subset para verificar rutas y formatos.

## 3. Normalización con CLAHE

* **Objetivo**: Mejorar contraste local sin amplificar demasiado el ruido, crítico en tinciones IHC.
* **Implementación**: Entonces se usaría OpenCV y su método `cv2.createCLAHE` (Contrast Limited AHE) aplicado al canal L de espacio Lab o en escala de grises ([PyImageSearch][3]).
* **Salida**: Se guarda cada imagen normalizada junto a la original para comparar visualmente.

## 4. Aumentación de datos

* **Librería**: Se configura un pipeline con Albumentations, que permite aplicar transformaciones espaciales (flip, rotación) sincronizadas con máscaras y sólo aplicar ajustes de color (hue, saturación) a la imagen ([Albumentations][4]).
* **Ejemplos**: Para cada imagen del subset, genera 3–5 variaciones aumentadas y visualízalas junto a su máscara de anotaciones.

## 5. Conteo de núcleos

* **Método simple**:

  1. Convierte la imagen normalizada a escala de grises.
  2. Aplica umbral adaptativo (`cv2.adaptiveThreshold`) o método de Otsu.
  3. Detecta contornos con `cv2.findContours` y filtra por área mínima.
  4. Cuenta y almacena el número de blobs detectados.
* **Validación manual**: Sobre 10 imágenes compara conteo automático vs. conteo de anotaciones para estimar error.

## 6. Cronograma semanal

| Semana       | Hito principal                                                                   |
| ------------ | -------------------------------------------------------------------------------- |
| **Semana 1** | Selección de subset (≈50 imágenes) + data loader funcional + visualización       |
| **Semana 2** | Implementación del módulo de normalización (CLAHE) y generación de comparativas  |
| **Semana 3** | Pipeline de aumentación con Albumentations y revisión visual de transformaciones |
| **Semana 4** | Conteo automático de núcleos, validación manual en 10 imágenes y reporte final   |

Con este MVP se tendrá a fin de mes un flujo end-to-end que carga tus datos, los normaliza, los aumenta y entrega recuentos básicos, listo para extenderse a un conjunto mayor o integrar modelos de deep learning. ¡Manos a la obra!

[1]: https://www.nature.com/articles/s41598-021-86912-w?utm_source=chatgpt.com "PathoNet introduced as a deep neural network backend for ... - Nature"
[2]: https://paperswithcode.com/dataset/shidc-bc-ki-67?utm_source=chatgpt.com "SHIDC-BC-Ki-67 Dataset - Papers With Code"
[3]: https://pyimagesearch.com/2021/02/01/opencv-histogram-equalization-and-adaptive-histogram-equalization-clahe/?utm_source=chatgpt.com "OpenCV Histogram Equalization and Adaptive ... - PyImageSearch"
[4]: https://albumentations.ai/docs/api-reference/augmentations/transforms/?utm_source=chatgpt.com "albumentations.augmentations.transforms"
