"""
gui/animations.py
Lightweight, elegant UI animation utilities for MBOX Viewer.
Uses native PySide6 QPropertyAnimation, QGraphicsOpacityEffect, and natural easing curves.
Zero dependencies on external animation libraries; non-blocking and memory efficient.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QTimer,
    Qt,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QProgressBar,
    QStackedWidget,
    QWidget,
)


# ----------------------------------------------------------------------
# Opacity & Fade Helpers
# ----------------------------------------------------------------------

def get_or_create_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    """Retrieve existing QGraphicsOpacityEffect or install a new one."""
    eff = widget.graphicsEffect()
    if isinstance(eff, QGraphicsOpacityEffect):
        return eff
    new_eff = QGraphicsOpacityEffect(widget)
    new_eff.setOpacity(1.0)
    widget.setGraphicsEffect(new_eff)
    return new_eff


def fade_in(
    widget: QWidget,
    duration: int = 200,
    start_opacity: float = 0.0,
    end_opacity: float = 1.0,
    easing: QEasingCurve.Type = QEasingCurve.OutCubic,
    on_finished: Optional[Callable[[], None]] = None,
) -> QPropertyAnimation:
    """Smoothly fade in a widget by animating its opacity."""
    widget.setVisible(True)
    eff = get_or_create_opacity_effect(widget)
    eff.setOpacity(start_opacity)

    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_opacity)
    anim.setEndValue(end_opacity)
    anim.setEasingCurve(easing)

    if on_finished:
        anim.finished.connect(on_finished)

    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def fade_out(
    widget: QWidget,
    duration: int = 150,
    start_opacity: float = 1.0,
    end_opacity: float = 0.0,
    easing: QEasingCurve.Type = QEasingCurve.InCubic,
    hide_on_finished: bool = True,
    on_finished: Optional[Callable[[], None]] = None,
) -> QPropertyAnimation:
    """Smoothly fade out a widget by animating its opacity."""
    eff = get_or_create_opacity_effect(widget)
    eff.setOpacity(start_opacity)

    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setDuration(duration)
    anim.setStartValue(start_opacity)
    anim.setEndValue(end_opacity)
    anim.setEasingCurve(easing)

    def _cleanup():
        if hide_on_finished:
            widget.setVisible(False)
        if on_finished:
            on_finished()

    anim.finished.connect(_cleanup)
    anim.start(QPropertyAnimation.DeleteWhenStopped)
    return anim


def cross_fade_stacked(
    stacked_widget: QStackedWidget,
    target_index: int,
    duration: int = 200,
    on_finished: Optional[Callable[[], None]] = None,
) -> None:
    """
    Seamless cross-fade transition between pages in a QStackedWidget.
    Switches to target page immediately and smoothly fades it in.
    """
    if target_index == stacked_widget.currentIndex():
        return

    next_widget = stacked_widget.widget(target_index)
    stacked_widget.setCurrentIndex(target_index)

    if next_widget:
        fade_in(next_widget, duration=duration, on_finished=on_finished)
    elif on_finished:
        on_finished()


# ----------------------------------------------------------------------
# Interactive Hover Card Lift Effect
# ----------------------------------------------------------------------

class HoverCardFilter(QObject):
    """
    Event filter installed on cards/frames.
    Provides smooth hover lift, border glow highlight, and pointer cursor.
    """

    def __init__(self, target_widget: QWidget, lift_px: int = 2, parent: Optional[QObject] = None):
        super().__init__(parent or target_widget)
        self._target = target_widget
        self._lift_px = lift_px
        self._original_pos: Optional[QPoint] = None
        self._pos_anim: Optional[QPropertyAnimation] = None

        self._target.setMouseTracking(True)
        self._target.setCursor(Qt.PointingHandCursor)
        self._target.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched == self._target:
            if event.type() == QEvent.Enter:
                self._on_enter()
            elif event.type() == QEvent.Leave:
                self._on_leave()
        return super().eventFilter(watched, event)

    def _on_enter(self):
        if not self._target.isEnabled():
            return
        if self._original_pos is None:
            self._original_pos = self._target.pos()

        if self._pos_anim and self._pos_anim.state() == QPropertyAnimation.Running:
            self._pos_anim.stop()

        target_y = self._original_pos.y() - self._lift_px
        self._pos_anim = QPropertyAnimation(self._target, b"pos", self)
        self._pos_anim.setDuration(120)
        self._pos_anim.setStartValue(self._target.pos())
        self._pos_anim.setEndValue(QPoint(self._original_pos.x(), target_y))
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim.start(QPropertyAnimation.DeleteWhenStopped)

    def _on_leave(self):
        if self._original_pos is None:
            return
        if self._pos_anim and self._pos_anim.state() == QPropertyAnimation.Running:
            self._pos_anim.stop()

        self._pos_anim = QPropertyAnimation(self._target, b"pos", self)
        self._pos_anim.setDuration(150)
        self._pos_anim.setStartValue(self._target.pos())
        self._pos_anim.setEndValue(self._original_pos)
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim.start(QPropertyAnimation.DeleteWhenStopped)


# ----------------------------------------------------------------------
# Smooth Progress Bar Interpolator
# ----------------------------------------------------------------------

def animate_progress_bar(
    pbar: QProgressBar,
    target_value: int,
    duration: int = 150,
) -> None:
    """
    Smoothly animates a QProgressBar to target_value using OutCubic easing
    instead of instant jumpy increments.
    """
    if not pbar.isVisible():
        pbar.setValue(target_value)
        return

    old_anim = getattr(pbar, "_value_anim", None)
    if old_anim and old_anim.state() == QPropertyAnimation.Running:
        old_anim.stop()

    curr_val = pbar.value()
    if curr_val == target_value:
        return

    anim = QPropertyAnimation(pbar, b"value", pbar)
    anim.setDuration(duration)
    anim.setStartValue(curr_val)
    anim.setEndValue(target_value)
    anim.setEasingCurve(QEasingCurve.OutCubic)
    setattr(pbar, "_value_anim", anim)
    anim.start(QPropertyAnimation.DeleteWhenStopped)


# ----------------------------------------------------------------------
# Pulse & Flash Feedback Helpers
# ----------------------------------------------------------------------

def pulse_widget(
    widget: QWidget,
    min_opacity: float = 0.5,
    max_opacity: float = 1.0,
    duration: int = 350,
    on_finished: Optional[Callable[[], None]] = None,
) -> None:
    """Gentle breathing pulse animation for status badges or drop zones."""
    eff = get_or_create_opacity_effect(widget)

    group = QSequentialAnimationGroup(widget)
    fade_down = QPropertyAnimation(eff, b"opacity", group)
    fade_down.setDuration(duration // 2)
    fade_down.setStartValue(max_opacity)
    fade_down.setEndValue(min_opacity)
    fade_down.setEasingCurve(QEasingCurve.InOutQuad)

    fade_up = QPropertyAnimation(eff, b"opacity", group)
    fade_up.setDuration(duration // 2)
    fade_up.setStartValue(min_opacity)
    fade_up.setEndValue(max_opacity)
    fade_up.setEasingCurve(QEasingCurve.InOutQuad)

    group.addAnimation(fade_down)
    group.addAnimation(fade_up)

    if on_finished:
        group.finished.connect(on_finished)

    group.start(QPropertyAnimation.DeleteWhenStopped)
