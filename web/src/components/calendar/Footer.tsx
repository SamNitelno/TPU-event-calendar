import { Link } from "@tanstack/react-router";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-[1440px] flex-col gap-3 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <p>Календарь мероприятий Томского политехнического университета</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2">
          <Link to="/" className="hover:text-primary">Афиша</Link>
          <Link to="/guide" className="hover:text-primary">Как пользоваться</Link>
          <Link to="/submit" className="hover:text-primary">Подать мероприятие</Link>
          <Link to="/admin" className="hover:text-primary">Администратору</Link>
        </div>
      </div>
    </footer>
  );
}
