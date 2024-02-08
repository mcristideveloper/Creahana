import numpy as np
import pandas as pd

def Factores_MATLAB(largo, alpha):
    """ Factores para Decay
        De esta forma es que MATLAB calcula sus vectores de factores logaritmicamente espaciados.

        Factores_values = []
        for i in range(largo):
            if alpha == 1:
                Factores_values.append(1)
            else:
                Factores_values.append(np.power(alpha, i))
        return Factores_values

    """
    if alpha == 1:
        return pd.DataFrame([1] * largo)
    else:
        return pd.DataFrame(np.geomspace(1, alpha ** (largo - 1), largo))

def Promedio_MATLAB(values, alpha, factors):
    # N° efectivo de observaciones, según el decay factor
    if alpha == 1:
        Obs = len(values)
    else:
        Obs = (1 - np.power(alpha, len(values))) / (1 - alpha)

    # Calcula Promedio usando el vector de Factores y la variable de Observaciones Efectivas
    Promedio = 0
    for i in range(len(values)):
        Promedio = Promedio + factors[i] * values[i]
    Promedio = Promedio / Obs
    return Promedio

def Promedio(df_retornos, alpha, factors):
    """
        # Calcula Promedio usando el vector de Factores y la variable de Observaciones Efectivas
        Promedio = 0
        for i in range(largo):
                Promedio = Promedio + factors[i] * values[i]
    """
    """
        El dataframe de retornos debe llegar sin fecha.
    """
    largo = df_retornos.shape[0]
    # N° efectivo de observaciones, según el decay factor
    if alpha == 1:
        return pd.DataFrame(df_retornos.mean())
    else:
        Obs = (1 - np.power(alpha, largo)) / (1 - alpha)
        return df_retornos.mul(factors[0], axis=0).sum() / Obs

def Covarianza_MATLAB(values_x, values_y, alpha, factors):
    # N° efectivo de observaciones, según el decay factor
    if alpha == 1:
        Obs = len(values_x)
    else:
        Obs = (1 - np.power(alpha, len(values_x))) / (1 - alpha)

    # Promedios de cada Variable
    prom_x = Promedio_MATLAB(values_x, alpha, factors)
    prom_y = Promedio_MATLAB(values_y, alpha, factors)

    # Calcula Covarianza usando el vector de Factores, Promedio y la variable de Observaciones Efectivas
    Covarianza = 0
    for i in range(len(values_x)):
        Covarianza = Covarianza + factors[i] * (values_x[i] - prom_x) * (values_y[i] - prom_y)
    Covarianza = Covarianza / Obs
    return Covarianza

def Covarianza(df_promedios, df_retornos, df_factores, alpha):
    if alpha == 1:
        return df_retornos.cov()
    else:
        MCovar = []
        n_papeles = df_promedios.shape[0]
        diferencias = (df_retornos-df_promedios)
        np_factores = np.array(df_factores).T
        Obs = (1 - np.power(alpha, df_retornos.shape[0])) / (1 - alpha)
        for i in range(n_papeles):
            temp = np.array(diferencias.iloc[:, i])
            temp = np_factores*temp
            cov_num = diferencias.transpose().mul(temp[0]).transpose().sum()/Obs
            MCovar.append(cov_num.values)
        return pd.DataFrame(MCovar)
