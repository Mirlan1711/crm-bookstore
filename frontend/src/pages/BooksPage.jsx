import { useEffect, useState } from "react";
import { createBook, deleteBook, getBooksPage, getCategories, updateBook } from "../services/api";
import Pagination from "../components/Pagination";

const emptyForm = { title: "", author: "", isbn: "", category: "", publisher: "", publication_year: "", description: "", price: "", stock_quantity: 0, low_stock_threshold: 2, is_active: true };

export default function BooksPage() {
  const [books, setBooks] = useState([]);
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [stock, setStock] = useState("");
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadBooks(targetPage = 1, filterOverrides = {}) {
    try {
      const currentSearch = filterOverrides.search ?? search;
      const currentStock = filterOverrides.stock ?? stock;
      const result = await getBooksPage({ page: targetPage, search: currentSearch || undefined, stock: currentStock || undefined });
      setBooks(result.items); setCount(result.count); setPage(targetPage);
    } catch (requestError) { setError(requestError.message); }
  }

  useEffect(() => {
    Promise.all([getCategories(), getBooksPage({ page: 1 })]).then(([loadedCategories, loadedBooks]) => {
      setCategories(loadedCategories.results || loadedCategories);
      setBooks(loadedBooks.items); setCount(loadedBooks.count);
    }).catch((requestError) => setError(requestError.message));
  }, []);

  function startEdit(book) {
    setEditingId(book.id);
    setForm({ title: book.title, author: book.author, isbn: book.isbn || "", category: book.category, publisher: book.publisher || "", publication_year: book.publication_year || "", description: book.description || "", price: book.price, stock_quantity: book.stock_quantity, low_stock_threshold: book.low_stock_threshold, is_active: book.is_active });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetForm() { setEditingId(null); setForm(emptyForm); }

  async function save(event) {
    event.preventDefault(); setError(""); setNotice("");
    try {
      const payload = { ...form, category: Number(form.category), price: Number(form.price), stock_quantity: Number(form.stock_quantity), low_stock_threshold: Number(form.low_stock_threshold), publication_year: form.publication_year ? Number(form.publication_year) : null };
      const saved = editingId ? await updateBook(editingId, payload) : await createBook(payload);
      setBooks((items) => editingId ? items.map((item) => item.id === saved.id ? saved : item) : [saved, ...items]);
      setNotice(editingId ? "Книга обновлена." : "Книга добавлена в каталог."); resetForm();
    } catch (requestError) { setError(requestError.message); }
  }

  async function remove(id) {
    if (!window.confirm("Удалить книгу из каталога?")) return;
    try { await deleteBook(id); setBooks((items) => items.filter((item) => item.id !== id)); setNotice("Книга удалена."); }
    catch (requestError) { setError(requestError.message); }
  }

  return <section>
    <div className="page-heading"><div><span className="eyebrow">КАТАЛОГ</span><h1>Книги</h1><p className="muted">Управление ассортиментом, ценами и остатками книжного магазина.</p></div></div>
    {error && <p className="error">{error}</p>}{notice && <p className="success">{notice}</p>}
    <div className="card form-card"><h2>{editingId ? "Редактирование книги" : "Новая книга"}</h2><form className="entity-form" onSubmit={save}>
      <input required placeholder="Название книги" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      <input required placeholder="Автор" value={form.author} onChange={(e) => setForm({ ...form, author: e.target.value })} />
      <input placeholder="ISBN" value={form.isbn} onChange={(e) => setForm({ ...form, isbn: e.target.value })} />
      <select required value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option value="">Категория</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select>
      <input placeholder="Издательство" value={form.publisher} onChange={(e) => setForm({ ...form, publisher: e.target.value })} />
      <input type="number" min="0" placeholder="Год издания" value={form.publication_year} onChange={(e) => setForm({ ...form, publication_year: e.target.value })} />
      <input required type="number" min="0" step="0.01" placeholder="Цена, ₽" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
      <input required type="number" min="0" placeholder="Остаток" value={form.stock_quantity} onChange={(e) => setForm({ ...form, stock_quantity: e.target.value })} />
      <input required type="number" min="0" placeholder="Порог остатка" value={form.low_stock_threshold} onChange={(e) => setForm({ ...form, low_stock_threshold: e.target.value })} />
      <textarea placeholder="Описание" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      <div className="form-actions"><button type="submit">{editingId ? "Сохранить" : "Добавить книгу"}</button>{editingId && <button type="button" className="secondary" onClick={resetForm}>Отмена</button>}</div>
    </form></div>
    <div className="card client-list"><div className="search-row"><input placeholder="Поиск по названию, автору или ISBN" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loadBooks(1)} /><button onClick={() => loadBooks(1)}>Найти</button><select value={stock} onChange={(e) => { const nextStock = e.target.value; setStock(nextStock); loadBooks(1, { stock: nextStock }); }}><option value="">Все остатки</option><option value="available">В наличии</option><option value="low">Мало на складе</option><option value="out">Нет в наличии</option></select></div>
      {books.length === 0 ? <p className="muted empty-state">Книги пока не добавлены.</p> : <div className="client-items">{books.map((book) => <article className="client-item" key={book.id}><div><h3>{book.title}</h3><p>{book.author} · {Number(book.price).toLocaleString("ru-RU")} ₽</p><span className="status-badge">{book.category_name}</span><span className={`date-label ${book.is_low_stock ? "is-overdue" : ""}`}> Остаток: {book.stock_quantity}</span>{book.isbn && <small className="muted"> ISBN {book.isbn}</small>}</div><div className="item-actions"><button className="secondary" onClick={() => startEdit(book)}>Изменить</button><button className="danger" onClick={() => remove(book.id)}>Удалить</button></div></article>)}</div>}
      <Pagination page={page} count={count} pageSize={10} onChange={loadBooks} />
    </div>
  </section>;
}
