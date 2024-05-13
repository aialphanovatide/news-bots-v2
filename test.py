import datetime
import pytz

# Obtener el tiempo actual en UTC
tiempo_actual_utc = datetime.datetime.utcnow()

# Convertir el tiempo de APScheduler a un objeto datetime
prox_run_time = datetime.datetime.fromtimestamp(1715290973.122975)

# Obtener la zona horaria local
zona_horaria_local = pytz.timezone('America/Argentina/Buenos_Aires')

# Convertir el tiempo a la zona horaria local
prox_run_time_local = prox_run_time.replace(tzinfo=pytz.utc).astimezone(zona_horaria_local)

print("Próximo run time en tu zona horaria local:", prox_run_time_local)
