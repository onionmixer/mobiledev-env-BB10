#ifndef APPLICATION_UI_HPP
#define APPLICATION_UI_HPP

#include <QObject>
#include <QString>

class ApplicationUI : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString message READ message NOTIFY messageChanged)
public:
    explicit ApplicationUI(QObject *parent = 0);
    QString message() const;
    Q_INVOKABLE void increment();
signals:
    void messageChanged();
private:
    int m_count;
};

#endif
