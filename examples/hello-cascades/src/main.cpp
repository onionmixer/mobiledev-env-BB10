#include "ApplicationUI.hpp"
#include <bb/cascades/Application>

Q_DECL_EXPORT int main(int argc, char **argv)
{
    bb::cascades::Application app(argc, argv);
    ApplicationUI ui;
    return bb::cascades::Application::exec();
}
