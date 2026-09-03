const staff = [
  {
    name: "อาจารย์ ปริญญา จันทร์แสงรัตน์",
    role: "หัวหน้าโครงการวิจัย",
    duty: "ออกแบบ และพัฒนาระบบ",
    email: "parinya_j@rmutt.ac.th",
    phone: "02 549 4137, 4195",
    image: "https://sci.rmutt.ac.th/wp-content/uploads/2022/07/Parinya-Jansongrat.jpg",
  },
  {
    name: "อาจารย์จริญญา ทะหลวย",
    role: "นักวิเคราะห์และออกแบบระบบ",
    duty: "ออกแบบระบบฐานข้อมูล",
    email: "jarinya_t@rmutt.ac.th",
    phone: "02 549 4137, 4195",
    image: "https://sci.rmutt.ac.th/wp-content/uploads/2026/05/Jarinya-Thaloey.jpg",
  },
  {
    name: "ดร.ณัฎฐ์ ย่องหิ้น",
    role: "นักวิเคราะห์ข้อมูล",
    duty: "วิเคราะห์ข้อมูลและโมเดล AI",
    email: "nat_y@rmutt.ac.th",
    phone: "02 549 4137, 4195",
    image: "https://sci.rmutt.ac.th/wp-content/uploads/2026/04/NAT-YONGHINT.png",
  },
] as const;

export default function AboutUs() {
  return (
    <section className="about" id="about" aria-labelledby="about-title">
      <div className="about-heading">
        <div>
          <p className="eyebrow">THE TEAM BEHIND THE SYSTEM</p>
          <h2 id="about-title">About Us</h2>
        </div>
        <p>ทีมงานผู้ออกแบบ พัฒนา และวิเคราะห์ข้อมูลของระบบติดตามสภาพแปลงทุเรียน</p>
      </div>
      <div className="staff-grid">
        {staff.map((person) => (
          <article className="staff-card" key={person.email}>
            <div className="staff-photo-wrap">
              <img className="staff-photo" src={person.image} alt={`ภาพบุคลากร ${person.name}`} />
            </div>
            <div className="staff-content">
              <p className="staff-role">{person.role}</p>
              <h3>{person.name}</h3>
              <p className="staff-duty"><strong>หน้าที่</strong>{person.duty}</p>
              <div className="staff-contact">
                <a href={`mailto:${person.email}`}>{person.email}</a>
                <a href={`tel:${person.phone.replaceAll(" ", "")}`}>{person.phone}</a>
              </div>
            </div>
          </article>
        ))}
      </div>
      <p className="about-source">
        ข้อมูลบุคลากรและรูปภาพอ้างอิงจาก <a href="https://sci.rmutt.ac.th/staff-bd/" target="_blank" rel="noreferrer">เว็บไซต์คณะวิทยาศาสตร์และเทคโนโลยี มทร.ธัญบุรี</a>
      </p>
    </section>
  );
}
