# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.

#                           .=     ,        =.
#                   _  _   /'/    )\,/,/(_   \ \
#                    `//-.|  (  ,\\)\//\)\/_  ) |
#                    //___\   `\\\/\\/\/\\///'  /
#                 ,-"~`-._ `"--'_   `"'"`  _ \`'"~-,_
#                 \       `-.  '_`.      .'_` \ ,-"~`/
#                  `.__.-'`/  ( -\        /- )|-.__,'
#                    ||   |    \ O)  /^\ (O / |
#                    `\\  |         /   `\    /
#                      \\  \       /      `\ /
#                       `\\ `-.  /' .---.--.\
#                         `\\/`~(, '()      ('
#                          /(O) \\   _,.-.,_)
#                         //  \\ `\'`      /
#                        / |  ||   `""'"~"`
#                      /'  |__||
#                            `o
#      ___       _                    _          ___
#     / _ \___ _(_)__ __ __     ___  (_)__  ___ / (_)__  ___
#    / // / _ `/ (_-</ // /    / _ \/ / _ \/ -_) / / _ \/ -_)
#   /____/\_,_/_/___/\_, /    / .__/_/ .__/\__/_/_/_//_/\__/
#                   /___/    /_/    /_/
#
#   by Noa Escourbanies, Leeloo Trinh-Thieu et Thomas Rubio
#   art by Joan G. Stark (Spunk)

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

import os, json, datetime

from PrismUtils.Decorators import err_catcher_plugin as err_catcher

BIRTHDAY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib", "birthdays.json")


class Prism_Daisy_Birthday_Functions(object):
    UPCOMING_DAYS = 7
    MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
                 "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

    # couleur d'accent de la bannière "aujourd'hui" selon l'hôte
    ACCENTS = {
        "Maya": "#5285a6",
        "Houdini": "#e8832a",
        "Standalone": "#7895a1",
    }

    def __init__(self, core, plugin):
        self.core = core
        self.plugin = plugin
        self.core.registerCallback("onProjectBrowserStartup", self.onProjectBrowserStartup, plugin=self.plugin)

    @err_catcher(name=__name__)
    def isActive(self):
        return True

    def loadBirthdays(self):
        if not os.path.exists(BIRTHDAY_FILE):
            return {}
        try:
            with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("[Daisy_Birthday] Lecture impossible : %s" % e)
            return {}

    def getBirthdays(self):
        today = datetime.date.today()
        todayNames, upcoming = [], []

        for name, mmdd in self.loadBirthdays().items():
            try:
                month, day = [int(x) for x in mmdd.split("-")]
                try:
                    date = datetime.date(today.year, month, day)
                except ValueError:  # 29 février sur une année non bissextile
                    date = datetime.date(today.year, 2, 28)
                if date < today:
                    date = date.replace(year=today.year + 1)
            except Exception:
                continue

            delta = (date - today).days
            if delta == 0:
                todayNames.append(name)
            elif 0 < delta <= self.UPCOMING_DAYS:
                upcoming.append((delta, name, date))

        upcoming.sort()
        return todayNames, upcoming

    def formatWhen(self, delta, date):
        if delta == 1:
            return "demain"
        return "le %d %s" % (date.day, self.MONTHS_FR[date.month - 1])

    def buildTodayText(self, todayNames):
        return "🎂  Joyeux anniversaire %s !  🎉" % " & ".join(todayNames)

    def buildText(self, todayNames, upcoming):
        parts = []
        if todayNames:
            parts.append(self.buildTodayText(todayNames))
        if upcoming:
            nxt = ", ".join(
                "%s %s" % (n, self.formatWhen(d, date))
                for d, n, date in upcoming
            )
            parts.append("C'est Bientôt l'Anniversaires de : %s" % nxt)
        return "     ·     ".join(parts)

    def getHostName(self):
        try:
            return self.core.appPlugin.pluginName
        except Exception:
            return "Standalone"

    def getColors(self, origin, today):
        pal = origin.palette()
        base = pal.color(QPalette.Window)
        text = pal.color(QPalette.WindowText)

        if today:
            accent = QColor(self.ACCENTS.get(self.getHostName(), self.ACCENTS["Standalone"]))
            # texte clair ou sombre selon la luminosité de l'accent
            fg = QColor("#ffffff") if accent.lightness() < 150 else QColor("#1e1e1e")
            return accent, fg

        # barre discrète : légèrement décalée par rapport au fond de la fenêtre
        bg = base.lighter(115) if base.lightness() < 128 else base.darker(108)
        return bg, text

    def onProjectBrowserStartup(self, origin):
        todayNames, upcoming = self.getBirthdays()
        if not todayNames and not upcoming:
            return

        bar = QToolBar("Anniversaires", origin)
        bar.setObjectName("BirthdayBanner")
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setStyleSheet("QToolBar { spacing: 0; padding: 0; border: 0; }")

        text = self.buildText(todayNames, upcoming)
        bg, fg = self.getColors(origin, bool(todayNames))
        if todayNames:
            label = MarqueeLabel(text, bg, fg, size=14, bold=True, padding=6,
                                 intro=self.buildTodayText(todayNames), hold=3000)
        else:
            label = MarqueeLabel(text, bg, fg, size=12, padding=4)

        bar.addWidget(label)
        origin.addToolBar(Qt.TopToolBarArea, bar)


class MarqueeLabel(QWidget):
    def __init__(self, text, bg, fg, size=12, bold=False, padding=4, speed=1, interval=30, intro=None, hold=3000, parent=None):
        super(MarqueeLabel, self).__init__(parent)
        self.text = text
        self.intro = intro
        self.bg = QColor(bg)
        self.fg = QColor(fg)
        self.speed = speed
        self.interval = interval
        self.gap = 80  # espace entre deux répétitions
        self.offset = 0

        font = self.font()
        font.setPixelSize(size)
        font.setBold(bold)
        self.setFont(font)

        self.setFixedHeight(self.fontMetrics().height() + padding * 2)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.step)

        if intro:
            QTimer.singleShot(hold, self.startScroll)
        else:
            self.startScroll()

    def startScroll(self):
        self.intro = None
        self.offset = -self.width()  # le texte entre par la droite
        self.timer.start(self.interval)

    def unitWidth(self):
        return self.fontMetrics().horizontalAdvance(self.text) + self.gap

    def step(self):
        self.offset += self.speed
        if self.offset >= self.unitWidth():
            self.offset -= self.unitWidth()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), self.bg)
        p.setPen(self.fg)

        if self.intro:
            p.drawText(self.rect(), Qt.AlignCenter, self.intro)
            return

        fm = self.fontMetrics()
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        x = -self.offset
        unit = self.unitWidth()
        while x < self.width():
            p.drawText(x, y, self.text)
            x += unit