#include "ApplicationUI.hpp"
#include <bb/cascades/Application>
#include <bb/cascades/AbstractPane>
#include <bb/cascades/QmlDocument>
#include <QDebug>
#include <QtGlobal>
#include <cstdlib>

ApplicationUI::ApplicationUI(QObject *parent) : QObject(parent), m_count(0)
{
    bb::cascades::QmlDocument *qml = bb::cascades::QmlDocument::create(
            "asset:///main.qml").parent(this);
    qml->setContextProperty("app", this);
    bb::cascades::AbstractPane *root = qml->createRootObject<bb::cascades::AbstractPane>();
    if (!root) {
        qCritical() << "Cannot load asset:///main.qml";
        std::exit(EXIT_FAILURE);
    }
    bb::cascades::Application::instance()->setScene(root);
}

QString ApplicationUI::message() const
{
    return QString("Qt %1 / button count: %2").arg(QT_VERSION_STR).arg(m_count);
}

void ApplicationUI::increment()
{
    ++m_count;
    emit messageChanged();
}
