from datetime import UTC, datetime

from app.models.maintenance import WorkOrder, WorkOrderStatus


class InvalidWorkOrderTransition(ValueError):
    pass


ALLOWED_TRANSITIONS: dict[WorkOrderStatus, frozenset[WorkOrderStatus]] = {
    WorkOrderStatus.OPEN: frozenset({WorkOrderStatus.TRIAGED, WorkOrderStatus.CANCELLED}),
    WorkOrderStatus.TRIAGED: frozenset({WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.CANCELLED}),
    WorkOrderStatus.IN_PROGRESS: frozenset({WorkOrderStatus.RESOLVED, WorkOrderStatus.CANCELLED}),
    WorkOrderStatus.RESOLVED: frozenset({WorkOrderStatus.CLOSED, WorkOrderStatus.IN_PROGRESS}),
    WorkOrderStatus.CLOSED: frozenset(),
    WorkOrderStatus.CANCELLED: frozenset(),
}


def transition_work_order(work_order: WorkOrder, target: WorkOrderStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[work_order.status]:
        raise InvalidWorkOrderTransition(
            f"Cannot move a work order from {work_order.status.value} to {target.value}"
        )
    now = datetime.now(UTC)
    work_order.status = target
    if target == WorkOrderStatus.RESOLVED:
        work_order.resolved_at = now
    elif target == WorkOrderStatus.IN_PROGRESS:
        work_order.resolved_at = None
    elif target in {WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED}:
        work_order.closed_at = now
