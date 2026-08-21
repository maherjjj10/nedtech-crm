import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  Check,
  CheckCheck,
  X,
  UserPlus,
  ListChecks,
  FileText,
  AlertCircle,
  Info,
  Clock,
} from "lucide-react";

import { api } from "../../lib/apiClient";
import { Button } from "../ui/button";


function getNotificationIcon(type) {
  switch (type) {
    case "client_created":
      return UserPlus;

    case "task_created":
    case "task_assigned":
      return ListChecks;

    case "invoice_created":
    case "invoice_due":
      return FileText;

    case "warning":
      return AlertCircle;

    case "info":
    default:
      return Info;
  }
}


function formatTime(dateString) {
  if (!dateString) {
    return "";
  }

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const now = new Date();

  const diff = Math.floor(
    (now.getTime() - date.getTime()) / 1000
  );

  if (diff < 60) {
    return "Just now";
  }

  if (diff < 3600) {
    return `${Math.floor(diff / 60)}m ago`;
  }

  if (diff < 86400) {
    return `${Math.floor(diff / 3600)}h ago`;
  }

  if (diff < 604800) {
    return `${Math.floor(diff / 86400)}d ago`;
  }

  return date.toLocaleDateString();
}


export default function NotificationBell() {
  const navigate = useNavigate();

  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const wrapperRef = useRef(null);


  const loadNotifications = useCallback(
    async (silent = false) => {
      try {
        if (!silent) {
          setLoading(true);
        }

        const response = await api.get(
          "/notifications?limit=50"
        );

        const data = response?.data || {};

        setNotifications(
          Array.isArray(data.items)
            ? data.items
            : []
        );

        setUnreadCount(
          Number(data.unread_count || 0)
        );
      } catch (error) {
        /*
         * Do not break the entire application
         * if notifications fail.
         */
        console.error(
          "Failed to load notifications:",
          error
        );
      } finally {
        if (!silent) {
          setLoading(false);
        }
      }
    },
    []
  );


  useEffect(() => {
    loadNotifications();

    const interval = setInterval(() => {
      loadNotifications(true);
    }, 30000);

    return () => {
      clearInterval(interval);
    };
  }, [loadNotifications]);


  useEffect(() => {
    function handleOutsideClick(event) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(
          event.target
        )
      ) {
        setOpen(false);
      }
    }

    if (open) {
      document.addEventListener(
        "mousedown",
        handleOutsideClick
      );
    }

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
    };
  }, [open]);


  async function markAsRead(notification) {
    if (!notification?.id) {
      return;
    }

    try {
      if (!notification.read) {
        await api.patch(
          `/notifications/${notification.id}/read`
        );

        setNotifications((current) =>
          current.map((item) =>
            item.id === notification.id
              ? {
                  ...item,
                  read: true,
                }
              : item
          )
        );

        setUnreadCount((count) =>
          Math.max(0, count - 1)
        );
      }
    } catch (error) {
      console.error(
        "Failed to mark notification as read:",
        error
      );
    }
  }


  async function handleNotificationClick(
    notification
  ) {
    await markAsRead(notification);

    setOpen(false);

    if (notification.url) {
      navigate(notification.url);
      return;
    }

    if (
      notification.entity_type === "client" &&
      notification.entity_id
    ) {
      navigate(
        `/clients/${notification.entity_id}`
      );
      return;
    }

    if (
      notification.entity_type === "task"
    ) {
      navigate("/tasks");
    }
  }


  async function markAllAsRead() {
    if (unreadCount === 0) {
      return;
    }

    try {
      await api.patch(
        "/notifications/read-all"
      );

      setNotifications((current) =>
        current.map((item) => ({
          ...item,
          read: true,
        }))
      );

      setUnreadCount(0);
    } catch (error) {
      console.error(
        "Failed to mark all notifications as read:",
        error
      );
    }
  }


  return (
    <div
      ref={wrapperRef}
      className="relative"
    >
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => {
          setOpen((value) => !value);

          if (!open) {
            loadNotifications();
          }
        }}
        aria-label="Notifications"
        data-testid="notification-bell"
      >
        <Bell className="h-5 w-5" />

        {unreadCount > 0 && (
          <span
            className="
              absolute
              -right-0.5
              -top-0.5
              min-w-[18px]
              h-[18px]
              px-1
              rounded-full
              bg-foreground
              text-background
              text-[10px]
              font-bold
              flex
              items-center
              justify-center
              leading-none
            "
          >
            {unreadCount > 99
              ? "99+"
              : unreadCount}
          </span>
        )}
      </Button>


      {open && (
        <div
          className="
            absolute
            right-0
            top-full
            mt-2
            w-[360px]
            max-w-[calc(100vw-24px)]
            rounded-xl
            border
            border-border
            bg-background
            shadow-xl
            z-[100]
            overflow-hidden
          "
          data-testid="notification-dropdown"
        >

          {/* HEADER */}
          <div
            className="
              flex
              items-center
              justify-between
              px-4
              py-3
              border-b
              border-border
            "
          >
            <div>
              <div className="font-semibold text-sm">
                Notifications
              </div>

              {unreadCount > 0 && (
                <div className="text-xs text-muted-foreground mt-0.5">
                  {unreadCount} unread
                </div>
              )}
            </div>


            <div className="flex items-center gap-1">

              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 text-xs"
                  onClick={markAllAsRead}
                >
                  <CheckCheck className="h-3.5 w-3.5 mr-1.5" />
                  Mark all read
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setOpen(false)}
              >
                <X className="h-4 w-4" />
              </Button>

            </div>
          </div>


          {/* CONTENT */}
          <div className="max-h-[420px] overflow-y-auto">

            {loading && notifications.length === 0 && (
              <div className="px-4 py-10 text-center">
                <div className="text-sm text-muted-foreground">
                  Loading notifications...
                </div>
              </div>
            )}


            {!loading &&
              notifications.length === 0 && (
                <div className="px-4 py-12 text-center">

                  <div
                    className="
                      mx-auto
                      h-10
                      w-10
                      rounded-full
                      bg-muted
                      flex
                      items-center
                      justify-center
                      mb-3
                    "
                  >
                    <Bell className="h-5 w-5 text-muted-foreground" />
                  </div>

                  <div className="text-sm font-medium">
                    No notifications
                  </div>

                  <div className="text-xs text-muted-foreground mt-1">
                    You're all caught up.
                  </div>

                </div>
              )}


            {notifications.map((notification) => {
              const Icon = getNotificationIcon(
                notification.type
              );

              return (
                <button
                  key={notification.id}
                  type="button"
                  onClick={() =>
                    handleNotificationClick(
                      notification
                    )
                  }
                  className={`
                    w-full
                    text-left
                    flex
                    gap-3
                    px-4
                    py-3
                    border-b
                    border-border/60
                    transition-colors
                    hover:bg-muted/60
                    ${
                      !notification.read
                        ? "bg-muted/30"
                        : "bg-background"
                    }
                  `}
                >

                  {/* ICON */}
                  <div
                    className="
                      h-9
                      w-9
                      shrink-0
                      rounded-full
                      bg-muted
                      flex
                      items-center
                      justify-center
                    "
                  >
                    <Icon className="h-4 w-4" />
                  </div>


                  {/* TEXT */}
                  <div className="flex-1 min-w-0">

                    <div className="flex items-start gap-2">

                      <div
                        className={`
                          text-sm
                          leading-5
                          truncate
                          ${
                            !notification.read
                              ? "font-semibold"
                              : "font-medium"
                          }
                        `}
                      >
                        {notification.title}
                      </div>

                      {!notification.read && (
                        <span
                          className="
                            mt-1.5
                            h-1.5
                            w-1.5
                            shrink-0
                            rounded-full
                            bg-foreground
                          "
                        />
                      )}

                    </div>


                    {notification.message && (
                      <div
                        className="
                          text-xs
                          text-muted-foreground
                          mt-0.5
                          line-clamp-2
                        "
                      >
                        {notification.message}
                      </div>
                    )}


                    <div
                      className="
                        flex
                        items-center
                        gap-1
                        mt-1.5
                        text-[11px]
                        text-muted-foreground
                      "
                    >
                      <Clock className="h-3 w-3" />

                      {formatTime(
                        notification.created_at
                      )}
                    </div>

                  </div>

                </button>
              );
            })}

          </div>


          {/* FOOTER */}
          {notifications.length > 0 && (
            <div
              className="
                px-4
                py-2.5
                border-t
                border-border
                bg-muted/20
              "
            >
              <div
                className="
                  text-[11px]
                  text-muted-foreground
                  flex
                  items-center
                  justify-center
                  gap-1
                "
              >
                <Check className="h-3 w-3" />
                Notifications update automatically
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}