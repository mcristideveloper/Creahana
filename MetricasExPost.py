import MarketFunctions as Func
import numpy as NP
from scipy import stats as SCI
from datetime import timedelta, date, datetime as dt
import pandas as pd

def SerieDecay(lambdafactor, numerodias):
    df = pd.DataFrame(columns=['Tiempo', 'Factor'])
    for i in range(0, numerodias):
        if lambdafactor == 1:
            df = df.append({'Tiempo': i, 'Factor': NP.power(lambdafactor, i)},
                           ignore_index=True)
        else:
            df = df.append({'Tiempo': i, 'Factor': (1 - lambdafactor) * NP.power(lambdafactor, i)},
                           ignore_index=True)
    return df

def VaR_Decay(Retornos, Factores, NivelConfianza):
    Cuadrados = NP.power(Retornos - NP.average(Retornos), 2)
    Cuadrados.reset_index(drop=True, inplace=True)
    VaR = NP.sqrt(sum(Factores * Cuadrados)) * SCI.norm.ppf(NivelConfianza) * NP.sqrt(20)
    return VaR

def MetricasExPost(conexion, Fecha, Dias, NivelConfianza):

    strconsulta_relativo = "{call dbo.AFP_SISTO (?, ?, ?, ?, ?, 0)}"
    strconsulta_absoluta = "{call dbo.AFP_SISTO (?, ?, ?, ?, ?, 1)}"

    Fin = Func.FechaAdd(Fecha, 1)
    Fecha = Func.Str_To_Date2(Fecha)
    Inicio = dt.strptime(Fecha, '%d/%m/%Y')
    Fin = Func.Str_To_Date2(Fin)
    Fin = dt.strptime(Fin, '%d/%m/%Y')

    #Inicio = date(2020, 7, 29)
    #Fin = date(2020, 7, 30)
    #NivelConfianza = 0.95
    #Dias = 20
    DecayFactor = 0.94
    for FechaMetrica in Func.Fechas(Inicio, Fin, timedelta):

        Fecha = FechaMetrica.strftime("%Y%m%d")

        params = [Fecha, Dias, '', '', '1D']

        datos_relativo = Func.Consulta(strconsulta_relativo, params, conexion)
        datos_absoluto = Func.Consulta(strconsulta_absoluta, params, conexion)
#draw puzzle draw one part
        if datos_relativo.FecData[0] != '0':
            Cuenta = Func.Serie_to_DataFrame(datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo'])['ExcesoRetorno'].count())
            Cuenta.columns = ['Cuenta']
            Filtro = Cuenta.Cuenta == Dias

            ### Tracking Error
            TrackingError = datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo'])['ExcesoRetorno'].std() * NP.sqrt(20)
            TrackingError = TrackingError.to_frame().reset_index()
            TrackingError.insert(4, 'Metrica', 'TE Ex Post')
            TrackingError.insert(5, 'VentanaDias', Dias)
            TrackingError = TrackingError[Filtro.values]
            TrackingError.columns = ['FecData', 'AFP', 'AFPBMK', 'Fondo', 'Metrica', 'VentanaDias', 'TE']

            ### Beta
            Beta = datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo']).apply(lambda datos_relativo: datos_relativo['Retorno'].cov(datos_relativo['RetornoAFPBMK']))/datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo']).apply(lambda datos_relativo: datos_relativo['RetornoAFPBMK'].var())
            Beta = Beta.to_frame().reset_index()
            Beta.insert(4, 'Metrica', 'Beta Ex Post')
            Beta.insert(5, 'VentanaDias', Dias)
            Beta = Beta[Filtro.values]

            ### IR / IR Sin Ajuste
            #Calcula Exceso Retorno para IR
            Exceso = datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo']).apply(lambda datos_relativo: (datos_relativo['Retorno'] + 1).prod())\
                     - datos_relativo.groupby(['FecData', 'AFP', 'AFPBMK', 'Fondo']).apply(lambda datos_relativo: (datos_relativo['RetornoAFPBMK'] + 1).prod())
            Exceso = Exceso.to_frame().reset_index()
            Exceso.columns = ['FecData', 'AFP', 'AFPBMK', 'Fondo', 'ExcesoRetorno']
            Exceso_SinAjuste = Exceso
            ### IR
            IR = Exceso.merge(TrackingError, how='inner',
                              left_on=["FecData", "AFP", "AFPBMK", "Fondo"],
                              right_on=["FecData", "AFP", "AFPBMK", "Fondo"])
            IR.insert(8, 'IR', (NP.power(1 + IR.ExcesoRetorno, 20 / Dias) - 1) / NP.power(IR.TE, IR.ExcesoRetorno/IR.ExcesoRetorno.abs()))
            IR.columns = ['FecData', 'AFP', 'AFPBMK', 'Fondo', 'TE', 'Metrica', 'VentanaDias', 'ExcesoRetorno', 'IR']
            del IR['ExcesoRetorno']
            del IR['TE']
            IR.Metrica = 'Information Ratio'

            ### IR Sin Ajuste
            IR_SinAjuste = Exceso_SinAjuste.merge(TrackingError, how='inner',
                              left_on=["FecData", "AFP", "AFPBMK", "Fondo"],
                              right_on=["FecData", "AFP", "AFPBMK", "Fondo"])
            IR_SinAjuste.insert(8, 'IR', (NP.power(1 + IR_SinAjuste.ExcesoRetorno, 20 / Dias) - 1) / IR_SinAjuste.TE)
            IR_SinAjuste.columns = ['FecData', 'AFP', 'AFPBMK', 'Fondo', 'TE', 'Metrica', 'VentanaDias', 'ExcesoRetorno', 'IR']
            del IR_SinAjuste['ExcesoRetorno']
            del IR_SinAjuste['TE']
            IR_SinAjuste.Metrica = 'Information Ratio Sin Ajuste'

            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? " \
                          "AND Metrica = 'Beta Ex Post' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)
            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? " \
                          "AND Metrica = 'TE Ex Post' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)
            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? " \
                          "AND Metrica = 'Information Ratio' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)
            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? " \
                          "AND Metrica = 'Information Ratio Sin Ajuste' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)

            ### Inserta los resultados de cada métrica
            Func.InsertarDatos(TrackingError, "MetricasExPost", conexion)
            Func.InsertarDatos(Beta, "MetricasExPost", conexion)
            Func.InsertarDatos(IR, "MetricasExPost", conexion)
            Func.InsertarDatos(IR_SinAjuste, "MetricasExPost", conexion)

        if datos_absoluto.FecData[0] != '0':
            Cuenta = Func.Serie_to_DataFrame(
                datos_absoluto.groupby(['FecData', 'AFP', 'Fondo'])['Retorno'].count())
            Cuenta.columns = ['Cuenta']
            Filtro = Cuenta.Cuenta == Dias

            ### VaR
            VaR = datos_absoluto.groupby(['FecData', 'AFP', 'Fondo'])['Retorno'].std() * SCI.norm.ppf(NivelConfianza) * NP.sqrt(20)
            VaR = VaR.to_frame().reset_index()
            VaR.insert(2, 'AFPBMK', '')
            VaR.insert(4, 'Metrica', 'VaR')
            VaR.insert(5, 'VentanaDias', Dias)
            VaR = VaR[Filtro.values]

            ### VaR con Decay
            fact = pd.DataFrame()
            fact_orig = SerieDecay(DecayFactor, Dias)
            datos = pd.DataFrame(datos_absoluto)
            for i in range(0, 7 * 5):
                fact = pd.concat([fact, fact_orig], axis=0)
            fact.drop(['Tiempo'], axis='columns', inplace=True)
            fact.reset_index()
            # if datos.shape[0] == fact.shape[0]:
            #     datos.insert(6, 'Factor', fact)
            #     datos_absoluto.drop(['Factor'], axis='columns', inplace=True)
            #     prom = datos.groupby(['FecData', 'AFP', 'Fondo'])['Retorno'].sum() / \
            #            datos.groupby(['FecData', 'AFP', 'Fondo'])['Retorno'].count()
            #     datos = pd.merge(datos, prom, on=['FecData', 'AFP', 'Fondo'], how='inner')
            #     datos.rename(columns={'Retorno_x': 'Retornos', 'Retorno_y': 'Promedio'}, inplace=True)
            #     datos.insert(8, 'CuadradosFactor', NP.power(datos.Retornos - datos.Promedio, 2) * datos.Factor)
            #     VaR_con_Decay = pd.DataFrame(
            #         NP.sqrt(datos.groupby(['FecData', 'AFP', 'Fondo'])['CuadradosFactor'].sum())
            #         * SCI.norm.ppf(NivelConfianza)
            #         * NP.sqrt(20))
            #     VaR_con_Decay.rename(columns={'CuadradosFactor': 'VaR_con_Decay'}, inplace=True)
            #     VaR_con_Decay = VaR_con_Decay.reset_index()
            #     VaR_con_Decay.insert(2, 'AFPBMK', '')
            #     VaR_con_Decay.insert(4, 'Metrica', 'VaR Decay')
            #     VaR_con_Decay.insert(5, 'VentanaDias', Dias)
            #     VaR_con_Decay = VaR_con_Decay[Filtro.values]

            ### Volatilidad
            Volatilidad = datos_absoluto.groupby(['FecData', 'AFP', 'Fondo'])['Retorno'].std() * NP.sqrt(20)
            Volatilidad = Volatilidad.to_frame().reset_index()
            Volatilidad.insert(2, 'AFPBMK', '')
            Volatilidad.insert(4, 'Metrica', 'Volatilidad')
            Volatilidad.insert(5, 'VentanaDias', Dias)
            Volatilidad = Volatilidad[Filtro.values]

            ### Sharpe
            Sharpe = NP.power(datos_absoluto.groupby(['FecData', 'AFP', 'Fondo']).apply(lambda datos_absoluto: (datos_absoluto['Retorno'] + 1).prod()), 20 / Dias) - 1
            Sharpe = Sharpe.to_frame().reset_index()
            Sharpe = Sharpe.merge(Volatilidad, how='inner', left_on=["FecData", "AFP", "Fondo"],
                                  right_on=["FecData", "AFP", "Fondo"])
            Sharpe.columns = ['FecData', 'AFP', 'Fondo', 'Retorno', 'AFPBMK', 'Metrica', 'VentanaDias', 'Volatilidad']
            Sharpe.insert(8, 'Sharpe', Sharpe.Retorno / Sharpe.Volatilidad)
            del Sharpe['AFPBMK']
            del Sharpe['Retorno']
            del Sharpe['Volatilidad']
            Sharpe.insert(2, 'AFPBMK', '')
            Sharpe.Metrica = 'Sharpe Ratio'

            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? AND Metrica = 'VaR' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)
            if datos.shape[0] == fact.shape[0]:
                streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? AND Metrica = 'VaR Decay' AND VentanaDias = " + str(Dias)
                Func.EjecutaSP(streliminar, Fecha, conexion)
            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? AND Metrica = 'Volatilidad' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)
            streliminar = "DELETE FROM MetricasExPost WHERE Fecha=? AND Metrica = 'Sharpe Ratio' AND VentanaDias = " + str(Dias)
            Func.EjecutaSP(streliminar, Fecha, conexion)

            ### Inserta los resultados de cada métrica
            Func.InsertarDatos(VaR, "MetricasExPost", conexion)
            # if datos.shape[0] == fact.shape[0]:
            #     Func.InsertarDatos(VaR_con_Decay, "MetricasExPost", conexion)
            Func.InsertarDatos(Volatilidad, "MetricasExPost", conexion)
            Func.InsertarDatos(Sharpe,"MetricasExPost", conexion)

        #print('Métricas Ex Post Generadas para el día: ' + Fecha)