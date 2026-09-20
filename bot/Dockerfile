FROM python:3.12-slim

# MPLCONFIGDIR уводим из HOME: иначе matplotlib на каждом старте ругается
# на недоступный каталог кэша и заново строит кэш шрифтов.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLCONFIGDIR=/app/.mplcache \
    STATE_FILE=/data/squirtcar_state.pickle

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY squirtcar ./squirtcar

# Прогреваем кэш шрифтов на сборке — иначе первый график в проде
# строится на десяток секунд дольше.
RUN mkdir -p "$MPLCONFIGDIR" \
 && python -c "import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt; plt.subplots()"

# Сюда Railway/Render монтируют диск, на котором переживает рестарты pickle
# с состоянием диалогов. Контейнер остаётся root'ом: том монтируется
# root-owned, и непривилегированный пользователь в него не запишет.
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "-m", "squirtcar.bot"]
