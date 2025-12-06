#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para cuantificar y comparar la complejidad de configuraciones de red.

- Recorre la carpeta ./configs y analiza los archivos de configuración.
- Cuenta únicamente líneas de código (omite líneas vacías y comentarios).
- Calcula métricas comparativas útiles para la tesis:
  * Número total de líneas por archivo.
  * Diferencia absoluta y porcentual respecto a la configuración más simple.
  * (Opcional) Diferencia respecto a una configuración de referencia (ej. MPLS tradicional).
- Genera un resumen en consola y un archivo CSV con los resultados.

Este script puede ser citado como soporte de la evaluación de complejidad
del proceso de implementación y despliegue (Capítulo 4).
"""

import os
import glob
import csv
from typing import List, Dict, Optional

# Carpeta donde se almacenan las configuraciones
CONFIG_DIR = "."

# Extensiones de archivos de configuración a considerar
EXTENSIONS = (".cfg", ".conf", ".txt", "")  # "" por si no tienen extensión

# Ignorar o no comentarios al contar las líneas
IGNORE_COMMENTS = True

# Prefijos típicos de comentarios en configuraciones de red
COMMENT_PREFIXES = ("#", "!", "//")


# Palabra clave para tomar un archivo como "referencia" (ej. MPLS tradicional)
# Si no se encuentra ninguno, simplemente no se calcularán métricas de referencia.
REFERENCIA_KEYWORD = "mpls"   # ej: "pe1-mpls.txt" será referencia


def es_linea_valida(linea: str) -> bool:
    """
    Determina si una línea debe considerarse como 'línea de código'.

    Criterios:
    - No está vacía.
    - Si IGNORE_COMMENTS es True, la línea no debe iniciar con un prefijo de comentario.
    """
    linea_limpia = linea.strip()

    # Omitir líneas vacías
    if not linea_limpia:
        return False

    # Omitir comentarios si está habilitado
    if IGNORE_COMMENTS and linea_limpia.startswith(COMMENT_PREFIXES):
        return False

    return True


def contar_lineas_config(ruta_archivo: str) -> int:
    """
    Cuenta el número de líneas válidas (líneas de código) en un archivo de configuración.
    """
    contador = 0
    with open(ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
        for linea in f:
            if es_linea_valida(linea):
                contador += 1
    return contador


def obtener_archivos_config(directorio: str) -> List[str]:
    """
    Devuelve la lista de archivos de configuración en el directorio indicado
    que coincidan con las extensiones definidas.
    """
    archivos = []

    # Si el usuario ha guardado archivos SIN extensión (ej. 'pe1-srv6')
    # también los recogemos comprobando ficheros "normales" sin filtrar por extensión.
    for entrada in os.listdir(directorio):
        ruta = os.path.join(directorio, entrada)
        if os.path.isfile(ruta):
            # Si la extensión está entre las permitidas (incluyendo cadena vacía)
            _, ext = os.path.splitext(entrada)
            if ext in EXTENSIONS:
                archivos.append(ruta)

    # Si quieres, se podría complementar con glob, pero con lo anterior suele bastar.
    return sorted(archivos)


def encontrar_referencia(resultados: List[Dict]) -> Optional[Dict]:
    """
    Busca un archivo de referencia (por ejemplo, la configuración MPLS tradicional)
    usando la palabra clave REFERENCIA_KEYWORD en el nombre del archivo.
    """
    for r in resultados:
        if REFERENCIA_KEYWORD.lower() in r["archivo"].lower() and "srv" not in r["archivo"].lower():
            return r
    return None


def guardar_csv(resultados: List[Dict], nombre_csv: str = "resumen_configuraciones.csv") -> None:
    """
    Guarda los resultados en un archivo CSV para uso posterior en tablas o gráficos.
    """
    campos = [
        "archivo",
        "lineas_codigo",
        "diff_vs_min_abs",
        "diff_vs_min_pct",
        "diff_vs_ref_abs",
        "diff_vs_ref_pct"
    ]

    with open(nombre_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos, delimiter=";")
        writer.writeheader()
        for r in resultados:
            writer.writerow(r)


def main():
    if not os.path.isdir(CONFIG_DIR):
        print(f"[ERROR] La carpeta de configuraciones no existe: {CONFIG_DIR}")
        print("Cree la carpeta y coloque dentro los archivos de configuración.")
        return

    archivos = obtener_archivos_config(CONFIG_DIR)

    if not archivos:
        print(f"[AVISO] No se encontraron archivos de configuración en: {CONFIG_DIR}")
        return

    resultados: List[Dict] = []

    print("Evaluación de complejidad de configuraciones (líneas de código):")
    print("-" * 80)

    # 1. Conteo de líneas por archivo
    for ruta in archivos:
        nombre = os.path.basename(ruta)
        num_lineas = contar_lineas_config(ruta)
        resultados.append(
            {
                "archivo": nombre,
                "lineas_codigo": num_lineas,
                # Estos campos se llenarán luego
                "diff_vs_min_abs": None,
                "diff_vs_min_pct": None,
                "diff_vs_ref_abs": None,
                "diff_vs_ref_pct": None,
            }
        )
        print(f"{nombre:35s} -> {num_lineas:5d} líneas de código")

    print("-" * 80)

    # 2. Ordenar por número de líneas (de menor a mayor)
    resultados_ordenados = sorted(resultados, key=lambda x: x["lineas_codigo"])
    mas_simple = resultados_ordenados[0]
    mas_complejo = resultados_ordenados[-1]

    min_lineas = mas_simple["lineas_codigo"]
    max_lineas = mas_complejo["lineas_codigo"]

    # 3. Buscar referencia (ej. MPLS tradicional)
    referencia = encontrar_referencia(resultados_ordenados)
    if referencia:
        ref_lineas = referencia["lineas_codigo"]
    else:
        ref_lineas = None

    # 4. Calcular diferencias vs mínimo y vs referencia
    for r in resultados_ordenados:
        lineas = r["lineas_codigo"]

        # Diferencia absoluta y porcentual respecto a la configuración más simple
        diff_min_abs = lineas - min_lineas
        diff_min_pct = (diff_min_abs / min_lineas * 100) if min_lineas > 0 else 0.0

        r["diff_vs_min_abs"] = diff_min_abs
        r["diff_vs_min_pct"] = round(diff_min_pct, 2)

        # Diferencia respecto a referencia (si existe)
        if ref_lineas is not None:
            diff_ref_abs = lineas - ref_lineas
            diff_ref_pct = (diff_ref_abs / ref_lineas * 100) if ref_lineas > 0 else 0.0
            r["diff_vs_ref_abs"] = diff_ref_abs
            r["diff_vs_ref_pct"] = round(diff_ref_pct, 2)

    # 5. Impresión del resumen comparativo
    print("\nResumen ordenado por complejidad (menos a más líneas):")
    for r in resultados_ordenados:
        print(
            f"- {r['archivo']:20s}: "
            f"{r['lineas_codigo']:4d} líneas  | "
            f"+{r['diff_vs_min_abs']:3d} vs mín "
            f"({r['diff_vs_min_pct']:6.2f} %)"
        )

    print("\nConfiguración con menor número de líneas (más sencilla de implementar):")
    print(f"> {mas_simple['archivo']} con {mas_simple['lineas_codigo']} líneas de código.")

    print("\nConfiguración con mayor número de líneas (más compleja):")
    print(f"> {mas_complejo['archivo']} con {mas_complejo['lineas_codigo']} líneas de código.")

    # Diferencia entre extremos
    diff_extremos = max_lineas - min_lineas
    diff_extremos_pct = (diff_extremos / max_lineas * 100) if max_lineas > 0 else 0.0
    print(
        f"\nDiferencia entre la configuración más simple y la más compleja: "
        f"{diff_extremos} líneas "
        f"({diff_extremos_pct:.2f} % del archivo más complejo)."
    )

    # Resumen respecto a referencia (si la hay)
    if referencia:
        print("\nArchivo de referencia identificado (ej. MPLS tradicional):")
        print(f"> {referencia['archivo']} con {referencia['lineas_codigo']} líneas.")
        print("Comparación frente a la referencia:")
        for r in resultados_ordenados:
            if r["diff_vs_ref_abs"] is None:
                continue
            signo = "+" if r["diff_vs_ref_abs"] >= 0 else ""
            print(
                f"- {r['archivo']:20s}: {r['lineas_codigo']:4d} líneas  | "
                f"{signo}{r['diff_vs_ref_abs']:4d} líneas vs ref "
                f"({r['diff_vs_ref_pct']:6.2f} %)"
            )
    else:
        print("\n[Nota] No se identificó un archivo de referencia que contenga la palabra 'mpls' sin 'srv'.")

    # 6. Guardar resultados en CSV
    guardar_csv(resultados_ordenados)
    print("\nSe ha generado el archivo 'resumen_configuraciones.csv' con el detalle de los resultados.")


if __name__ == "__main__":
    main()
