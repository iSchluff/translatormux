FROM debian:bullseye
ARG DEBIAN_FRONTEND=noninteractive

RUN sed -i "s/bullseye main/bullseye main non-free/" /etc/apt/sources.list
RUN apt update && apt upgrade -y
RUN apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-bad gstreamer1.0-plugins-good \
        pipenv locales git pkg-config libcairo2-dev libgirepository1.0-dev libgstreamer1.0-dev libfaac-dev

RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
