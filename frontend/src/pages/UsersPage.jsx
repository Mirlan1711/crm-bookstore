import { useEffect, useState } from "react";
import { createUser, getUsers, updateUser } from "../services/api";

const roles = {
  admin: "Администратор",
  supervisor: "Руководитель",
  manager: "Менеджер",
  user: "Пользователь",
};

const emptyForm = { username: "", email: "", password: "", password_confirm: "", first_name: "", last_name: "", phone: "", role: "user" };

export default function UsersPage({ currentUser }) {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const canManage = currentUser?.is_staff || currentUser?.role === "admin";

  async function loadUsers() {
    try { setUsers(await getUsers()); } catch (requestError) { setError(requestError.message); }
  }

  useEffect(() => { loadUsers(); }, []);

  function changeForm(event) { setForm({ ...form, [event.target.name]: event.target.value }); }

  function startEdit(user) {
    setEditingId(user.id);
    setForm({ username: user.username, email: user.email || "", password: "", password_confirm: "", first_name: user.first_name || "", last_name: user.last_name || "", phone: user.phone || "", role: user.role });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() { setEditingId(null); setForm(emptyForm); }

  async function save(event) {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const payload = { ...form };
      if (editingId) {
        delete payload.username;
        if (!payload.password) { delete payload.password; delete payload.password_confirm; }
      }
      const saved = editingId ? await updateUser(editingId, payload) : await createUser(payload);
      setUsers((items) => editingId ? items.map((item) => item.id === saved.id ? saved : item) : [...items, saved].sort((a, b) => a.username.localeCompare(b.username)));
      setMessage(editingId ? "Данные сотрудника обновлены." : "Аккаунт сотрудника создан.");
      resetForm();
    } catch (requestError) { setError(requestError.message); }
  }

  async function changeActive(user) {
    if (user.id === currentUser.id) return;
    setError(""); setMessage("");
    try {
      const saved = await updateUser(user.id, { is_active: !user.is_active });
      setUsers((items) => items.map((item) => item.id === saved.id ? saved : item));
      setMessage(`Пользователь ${user.username} ${saved.is_active ? "активирован" : "заблокирован"}.`);
    } catch (requestError) { setError(requestError.message); }
  }

  return <section>
    <div className="page-heading"><div><span className="eyebrow">КОМАНДА</span><h1>Сотрудники и роли</h1><p className="muted">Создание аккаунтов, назначение ролей и управление доступом к CRM.</p></div></div>
    {message && <p className="success">{message}</p>}{error && <p className="error">{error}</p>}
    {canManage && <div className="card employee-form-card"><div className="employee-form-heading"><div><h2>{editingId ? "Редактирование сотрудника" : "Новый сотрудник"}</h2><p className="muted">{editingId ? "Пароль можно оставить пустым, если менять его не нужно." : "Новый сотрудник сможет войти в CRM после создания аккаунта."}</p></div>{editingId && <button type="button" className="secondary" onClick={resetForm}>Отмена</button>}</div><form className="employee-form" onSubmit={save}>
      {!editingId && <label>Логин<input name="username" required value={form.username} onChange={changeForm} /></label>}
      <label>Email<input type="email" name="email" value={form.email} onChange={changeForm} /></label>
      <label>Имя<input name="first_name" value={form.first_name} onChange={changeForm} /></label>
      <label>Фамилия<input name="last_name" value={form.last_name} onChange={changeForm} /></label>
      <label>Телефон<input name="phone" value={form.phone} onChange={changeForm} /></label>
      <label>Роль<select name="role" value={form.role} onChange={changeForm}>{Object.entries(roles).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label>Пароль<input type="password" name="password" required={!editingId} value={form.password} onChange={changeForm} /></label>
      <label>Повторите пароль<input type="password" name="password_confirm" required={!editingId} value={form.password_confirm} onChange={changeForm} /></label>
      <div className="form-actions"><button type="submit">{editingId ? "Сохранить изменения" : "Создать аккаунт"}</button></div>
    </form></div>}
    <div className="card user-list">{users.length === 0 ? <p className="muted empty-state">Пользователи не найдены.</p> : <div className="client-items">{users.map((user) => <article className="client-item employee-item" key={user.id}><div className="employee-info"><h3>{user.first_name || user.username} {user.last_name}</h3><p>@{user.username} · {user.email || "Email не указан"}{user.phone ? ` · ${user.phone}` : ""}</p><div className="employee-badges"><span className={`status-badge ${user.is_active ? "" : "priority-high"}`}>{user.is_active ? "Активен" : "Заблокирован"}</span><span className="status-badge">{roles[user.role]}</span></div><div className="permission-list">{(user.permissions || []).map((permission) => <span key={permission}>{permission}</span>)}</div></div><div className="user-controls">{canManage && <><button className="secondary" onClick={() => startEdit(user)}>Изменить</button><button className="secondary" disabled={user.id === currentUser.id} onClick={() => changeActive(user)}>{user.is_active ? "Заблокировать" : "Активировать"}</button></>}</div></article>)}</div>}</div>
  </section>;
}
