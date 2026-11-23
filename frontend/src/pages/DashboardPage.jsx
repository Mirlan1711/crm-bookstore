import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { getDashboardStats } from "../services/api";
import BarChart from "../components/BarChart";

export default function DashboardPage({ user }) {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboardStats().then(setStats).catch((requestError) => setError(requestError.message));
  }, []);

  const cards = stats ? [
    ["Клиенты", stats.clients, "Всего в базе", "users"],
    ["Книги в каталоге", stats.books, "Активный ассортимент", "briefcase"],
    ["Активные заказы", stats.active_deals, "В работе сейчас", "calendar"],
    ["Низкий остаток", stats.low_stock_count, "Нужна закупка", "alert"],
  ] : [];

  return <section>
    <div className="dashboard-heading"><div><span className="eyebrow">BOOKSTORE CRM</span><h1>Панель управления</h1><p className="muted">{user ? `Хорошего дня, ${user.first_name || user.username}. Вот что происходит в магазине.` : "Продажи, каталог и задачи команды в одном месте."}</p></div><div className="dashboard-date"><span className="dashboard-date-dot" /> Обновлено сегодня</div></div>
    {error && <p className="error">{error}</p>}
    <div className="stats-grid">{cards.map(([title, value, caption, icon]) => <div className="card stat-card" key={title}><div className="stat-card-top"><span>{title}</span><span className={`stat-icon stat-icon-${icon}`}>{icon === "alert" ? "!" : icon === "calendar" ? "◷" : icon === "briefcase" ? "↗" : "•"}</span></div><strong>{value}</strong><small>{caption}</small></div>)}</div>
    {stats && <>
      <div className="dashboard-actions"><div><h2>Фокус на сегодня</h2><p className="muted">Быстрые действия для команды</p></div><div className="quick-actions"><Link to="/books">+ Добавить книгу</Link><Link to="/clients">+ Новый клиент</Link><Link to="/deals">+ Новый заказ</Link><Link to="/tasks">+ Новая задача</Link></div></div>
      <div className="dashboard-summary">
        <div className="card summary-highlight"><span className="eyebrow">ПРОДАЖИ В РАБОТЕ</span><h2>Сумма активных заказов</h2><strong className="summary-value">{Number(stats.deal_amount).toLocaleString("ru-RU")} ₽</strong><div className="summary-trend"><span>↗</span> Текущий портфель заказов</div></div>
        <div className="card summary-highlight"><span className="eyebrow">ЭФФЕКТИВНОСТЬ</span><h2>Завершённые заказы</h2><strong className="summary-value">{stats.conversion.rate}%</strong><p className="muted">Завершено {stats.conversion.completed} из {stats.conversion.total}</p></div>
        <div className="card chart-card"><h2>Заказы по статусам</h2><BarChart items={stats.deals_by_status.map((item) => ({ label: item.status__name, count: item.count }))} labelKey="label" valueKey="count" /></div>
        <div className="card chart-card"><h2>Продажи по месяцам</h2><BarChart items={stats.sales_by_month.map((item) => ({ label: item.month, total: item.total }))} labelKey="label" valueKey="total" formatter={(value) => `${value.toLocaleString("ru-RU")} ₽`} /></div>
        <div className="card chart-card"><h2>Популярные книги</h2><BarChart items={stats.top_books.map((item) => ({ label: item.title, quantity: item.quantity }))} labelKey="label" valueKey="quantity" formatter={(value) => `${value} шт.`} /></div>
        <div className="card chart-card"><h2>Продажи по категориям</h2><BarChart items={stats.sales_by_category.map((item) => ({ label: item.category, total: item.total }))} labelKey="label" valueKey="total" formatter={(value) => `${value.toLocaleString("ru-RU")} ₽`} /></div>
        <div className="card chart-card"><h2>Задачи по приоритетам</h2><BarChart items={stats.tasks_by_priority.map((item) => ({ label: item.priority === "high" ? "Высокий" : item.priority === "low" ? "Низкий" : "Средний", count: item.count }))} labelKey="label" valueKey="count" /></div>
        <div className="card chart-card"><h2>Активность менеджеров</h2><BarChart items={stats.manager_activity.map((item) => ({ label: item.username, count: item.count }))} labelKey="label" valueKey="count" /></div>
      </div>
      <div className="card low-stock-card"><div className="dashboard-section-heading"><div><h2>Книги с низким остатком</h2><p className="muted">Проверьте наличие перед следующей закупкой.</p></div><Link to="/books">Открыть каталог</Link></div>{stats.low_stock_books.length === 0 ? <p className="muted">Все позиции есть на складе.</p> : <div className="low-stock-list">{stats.low_stock_books.map((book) => <div className="low-stock-item" key={book.id}><div><strong>{book.title}</strong><span>{book.author}</span></div><b>{book.stock_quantity} шт.</b></div>)}</div>}</div>
    </>}
  </section>;
}
